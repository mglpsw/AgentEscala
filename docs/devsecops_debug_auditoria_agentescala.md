# AgentEscala — Guia prático de Debug + Auditoria de Segurança (DevSecOps)

> Escopo: homelab Proxmox/LXC + Nginx Proxy Manager (NPM/OpenResty) + backend FastAPI + frontend Vite + integrações OCR/Telegram.

---

## 0) Princípios de operação segura (antes de mudar qualquer coisa)

1. **Não derrubar SSH**: qualquer regra de firewall deve preservar 22/TCP (ou sua porta custom).
2. **Mudanças mínimas e reversíveis**: exporte configs antes de editar.
3. **Provar com evidência**: sempre validar com `curl -I`, `nginx -T`, `ss -lntp`, logs e teste externo.
4. **Não expor serviços internos**: backend e banco idealmente acessíveis apenas por rede interna/NPM.

Checklist de pré-mudança:

```bash
# Snapshot lógico de estado antes da intervenção
hostnamectl
ip -br a
ip r
ss -lntp
sudo iptables -S || true
sudo nft list ruleset || true
```

---

## 1) Acesso externo e redirecionamento (Infra + NPM)

## 1.1 Validar DNS, conectividade e certificado

No seu notebook/cliente externo:

```bash
# DNS autoritativo e resolução efetiva
nslookup escala.ks-sm.net
# ou
 dig +short escala.ks-sm.net A

# Certificado e SNI na porta 9443
openssl s_client -connect escala.ks-sm.net:9443 -servername escala.ks-sm.net </dev/null

# Cabeçalhos HTTP(S)
curl -k -sSI https://escala.ks-sm.net:9443/
curl -k -sSI https://escala.ks-sm.net:9443/login
```

Sinais esperados:
- Certificado apresentado para `escala.ks-sm.net` (CN/SAN coerente).
- `HTTP 200` em `/` e `/login` (ou `301/302` controlado para rota final).
- **Não** aparecer página default OpenResty.

## 1.2 Validar rota dentro do host Proxmox/LXC/NPM

No host onde está o NPM:

```bash
# Qual container é o NPM/OpenResty
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Image}}' | grep -Ei 'npm|nginx|openresty'

# Dump completo de config efetiva
NPM_CONTAINER="$(docker ps --format '{{.Names}}' | grep -Ei 'npm|nginx|openresty' | head -n1)"
docker exec "$NPM_CONTAINER" sh -c 'nginx -T' > /tmp/npm_nginx_dump.txt 2>&1

# Verificar host alvo
grep -n "escala.ks-sm.net" /tmp/npm_nginx_dump.txt
grep -n "server_name" /tmp/npm_nginx_dump.txt | head -n 200
grep -n "proxy_pass" /tmp/npm_nginx_dump.txt | head -n 200
grep -n "default_server" /tmp/npm_nginx_dump.txt
```

Procure por:
- `server_name escala.ks-sm.net;`
- bloco `server` correto para 443/9443 com SSL;
- `proxy_pass` apontando para frontend estável (não Vite temporário).

## 1.3 Garantir que backend interno não vaze IP

No backend/LXC:

```bash
# Mostrar binds ativos
ss -lntp | grep -E ':8030|:18000|:8020|:80|:443'

# Firewall (exemplos)
sudo ufw status verbose || true
sudo iptables -L -n -v || true
```

Recomendação:
- Backend ouvindo em IP interno/rede docker apenas.
- Exposição externa somente via NPM.
- Se possível, bloquear origem direta ao backend e aceitar apenas origem do NPM.

## 1.4 Testes de ponta-a-ponta (roteador -> Proxmox -> NPM)

```bash
# no roteador/proxmox: confirmar DNAT para porta externa desejada
# (comando depende da plataforma)

# no host NPM: confirmar chegada de tráfego
sudo tcpdump -ni any 'tcp port 9443' -c 20

# no backend alvo: confirmar tráfego proxyado pelo NPM
sudo tcpdump -ni any 'host <IP_DO_NPM> and tcp port 8030' -c 20
```

---

## 2) Segurança da integração Telegram (webhook)

## 2.1 Controles obrigatórios

1. **Segredo no caminho**: `/webhook/telegram/<token_longo_randomico>`.
2. **Header secreto**: use `X-Telegram-Bot-Api-Secret-Token` (definido no `setWebhook`).
3. **Allowlist de IP** (defesa em profundidade): validar IP de origem contra ranges oficiais Telegram (atualize periodicamente).
4. **Rate limiting** + payload size limit + timeout curto.
5. **Idempotência** por `update_id` (evita replay).

## 2.2 Exemplo FastAPI (header secreto + IP allowlist)

```python
# backend/api/telegram_webhook.py (exemplo)
from ipaddress import ip_address, ip_network
from fastapi import APIRouter, Header, HTTPException, Request, status

router = APIRouter(prefix="/telegram", tags=["telegram"])

TELEGRAM_SECRET = "trocar-por-segredo-forte"
TELEGRAM_ALLOWED_CIDRS = [
    ip_network("149.154.160.0/20"),
    ip_network("91.108.4.0/22"),
]


def _ip_allowed(ip: str) -> bool:
    ip_obj = ip_address(ip)
    return any(ip_obj in cidr for cidr in TELEGRAM_ALLOWED_CIDRS)


@router.post("/webhook/{path_token}")
async def telegram_webhook(
    path_token: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if path_token != "token-url-longo-e-aleatorio":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if x_telegram_bot_api_secret_token != TELEGRAM_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid secret")

    client_ip = request.client.host if request.client else "0.0.0.0"
    if not _ip_allowed(client_ip):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ip not allowed")

    payload = await request.json()
    # TODO: validar schema e update_id (idempotência)
    return {"ok": True}
```

> Observação: IP allowlist pode quebrar se você usar CDN/proxy sem preservar IP real. Nesses casos, valide `X-Forwarded-For` de forma segura apenas quando vier do seu reverse proxy confiável.

## 2.3 Registrar webhook com token secreto

```bash
curl -sS "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -d "url=https://escala.ks-sm.net:9443/telegram/webhook/<token-url-longo-e-aleatorio>" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

---

## 3) Validação segura (upload OCR + frontend + sanitização pós-OCR)

## 3.1 Backend: validação estrita de arquivo

Para o endpoint de upload, aplique:
- limite de tamanho (ex.: 10 MB);
- extensão permitida (`.pdf`, `.xlsx`, `.csv`);
- MIME detectado por conteúdo (`python-magic`, não só `content-type` do cliente);
- assinatura mágica (`%PDF-`, ZIP OOXML etc.);
- anti-zip-bomb e timeout de parsing;
- varredura malware (ClamAV, se possível);
- isolamento do worker OCR (fila + processo/contêiner separado com limites de CPU/memória).

Exemplo de validação utilitária:

```python
from pathlib import Path
from fastapi import HTTPException, UploadFile, status

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".xlsx", ".csv"}

async def read_and_validate_upload(file: UploadFile) -> bytes:
    name = file.filename or "upload.bin"
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="extensão não permitida")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="arquivo vazio")

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="arquivo excede limite")

    if ext == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="assinatura PDF inválida")

    return content
```

## 3.2 Frontend: validações antes de enviar

No cliente, valide **sem substituir validação backend**:
- extensão/MIME aceitáveis;
- tamanho máximo;
- bloquear múltiplos uploads concorrentes sem fila;
- exibir erro claro para usuário;
- checksum opcional (sha256) para auditoria.

Exemplo (React):

```js
const MAX = 10 * 1024 * 1024;
const allowed = [
  'application/pdf',
  'text/csv',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
];

function validateFile(file) {
  if (!file) return 'Selecione um arquivo';
  if (file.size > MAX) return 'Arquivo acima de 10MB';
  if (!allowed.includes(file.type)) return 'Formato não permitido';
  return null;
}
```

## 3.3 Sanitização pós-OCR

Pipeline recomendado:
1. normalizar unicode (NFKC);
2. remover caracteres de controle;
3. trim e collapse de espaços;
4. validar campos por regex/enum/datas;
5. parse robusto de datas/horas com timezone explícito;
6. persistência somente via ORM/queries parametrizadas.

Exemplo:

```python
import re
import unicodedata

def sanitize_text(raw: str) -> str:
    txt = unicodedata.normalize("NFKC", raw)
    txt = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt
```

---

## 4) Troubleshooting e logs (extração OCR e bot)

## 4.1 Estratégia mínima de observabilidade

1. **Correlation ID** por requisição (`X-Request-ID`).
2. Logs estruturados JSON com campos: `ts`, `level`, `service`, `route`, `request_id`, `user_id`, `import_id`, `duration_ms`, `error_code`.
3. Níveis:
   - `INFO`: fluxo normal (início/fim, contagens);
   - `WARNING`: validação falhou, retry, timeouts parciais;
   - `ERROR`: falha de negócio/integração;
   - `EXCEPTION`: stacktrace somente no backend (não para cliente).
4. Métricas: taxa de erro por endpoint, latência p95, tamanho médio de upload, tempo de OCR, backlog de fila.

## 4.2 Pontos de log no fluxo

- Upload recebido: `filename`, `size`, `mime`, `request_id`.
- Validação rejeitada: motivo claro.
- OCR start/end: duração, engine, páginas processadas.
- Parse de escala: linhas válidas/inválidas/duplicadas.
- Telegram send/update: status HTTP, retry count, tempo.

## 4.3 Exemplo de try/catch útil (sem vazar segredo)

```python
import logging
logger = logging.getLogger("agentescala.ocr")

try:
    result = run_ocr(file_bytes)
except TimeoutError:
    logger.warning("ocr_timeout import_id=%s", import_id)
    raise
except Exception:
    logger.exception("ocr_unhandled_error import_id=%s", import_id)
    raise
```

---

## 5) Hardening rápido (prioridade prática)

1. Forçar TLS moderno no NPM e redirecionar HTTP->HTTPS.
2. Definir HSTS (após confirmar HTTPS estável).
3. Restringir CORS no backend para domínios explícitos (evitar `*` em produção).
4. Rotacionar segredos (`SECRET_KEY`, token bot Telegram, webhook secret).
5. Implementar rate limit para login, webhook e upload.
6. Ativar backup + restore testado periodicamente.
7. Monitorar certificados e expiração (alerta antecipado).

---

## 6) Playbook de incidente (quando "caiu")

```bash
# 1) Confirma DNS
nslookup escala.ks-sm.net

# 2) Confirma cert/SNI
openssl s_client -connect escala.ks-sm.net:9443 -servername escala.ks-sm.net </dev/null | head -n 40

# 3) Confirma roteamento NPM
curl -k -sSI https://escala.ks-sm.net:9443/

# 4) Confirma config ativa do NPM
NPM_CONTAINER="$(docker ps --format '{{.Names}}' | grep -Ei 'npm|nginx|openresty' | head -n1)"
docker exec "$NPM_CONTAINER" sh -c 'nginx -T' | sed -n '1,260p'

# 5) Confirma backend alvo e logs
curl -sSI http://<IP_BACKEND>:8030/
docker logs --tail=200 <container_backend>
```

---

## 7) Nota específica para AgentEscala

- O backend já possui middleware de observabilidade e métricas Prometheus; mantenha isso e adicione `request_id` nos logs para amarrar upload/OCR/Telegram no mesmo fluxo.
- O endpoint de importação já valida tipo básico de arquivo; fortalecer com limite de tamanho, assinatura mágica e isolamento do OCR.
- Em produção, não deixe CORS aberto; configure `CORS_ALLOW_ORIGINS` com o(s) domínio(s) públicos reais.

