#!/bin/bash
set -euo pipefail

DOMAIN="${DOMAIN:-escala.ks-sm.net}"
PUBLIC_PORT="${PUBLIC_PORT:-9443}"
LOCAL_BASE_URL="${LOCAL_BASE_URL:-http://192.168.3.155:18000}"
PRINT_ONLY=false

usage() {
  cat <<USAGE
Uso: $0 [--domain DOMINIO] [--public-port PORTA] [--local-base-url URL] [--print-only]

Executa um checklist prático de validação de deploy/roteamento do AgentEscala no homelab.

Opções:
  --domain          Domínio público (default: escala.ks-sm.net)
  --public-port     Porta HTTPS pública (default: 9443)
  --local-base-url  URL local do backend (default: http://192.168.3.155:18000)
  --print-only      Apenas imprime os comandos sem executar
  -h, --help        Exibe esta ajuda
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --public-port)
      PUBLIC_PORT="$2"
      shift 2
      ;;
    --local-base-url)
      LOCAL_BASE_URL="$2"
      shift 2
      ;;
    --print-only)
      PRINT_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Erro: argumento inválido: $1"
      usage
      exit 1
      ;;
  esac
done

run_or_print() {
  local cmd="$1"
  if [[ "$PRINT_ONLY" == true ]]; then
    echo "$cmd"
  else
    printf "\n$ %s\n" "$cmd"
    bash -lc "$cmd" || true
  fi
}

echo "=== AgentEscala | Validação de Deploy Homelab ==="
echo "Domínio: $DOMAIN"
echo "Porta pública: $PUBLIC_PORT"
echo "URL local: $LOCAL_BASE_URL"

if [[ "$PRINT_ONLY" == true ]]; then
  printf "\n[modo print-only]\n"
fi

printf "\n## 1) Baseline\n"
run_or_print "hostnamectl"
run_or_print "ip -br a"
run_or_print "ip r"
run_or_print "ss -lntp"

printf "\n## 2) Saúde local\n"
run_or_print "curl -sSI ${LOCAL_BASE_URL}/"
run_or_print "curl -sSI ${LOCAL_BASE_URL}/health"
run_or_print "curl -sSI ${LOCAL_BASE_URL}/metrics"

printf "\n## 3) DNS e TLS externo\n"
run_or_print "nslookup ${DOMAIN}"
run_or_print "curl -k -sSI https://${DOMAIN}/"
run_or_print "curl -k -sSI https://${DOMAIN}/login"
run_or_print "openssl s_client -connect ${DOMAIN}:${PUBLIC_PORT} -servername ${DOMAIN} </dev/null | head -n 40"
run_or_print "curl -k -sSI https://${DOMAIN}:${PUBLIC_PORT}/"
run_or_print "curl -k -sSI https://${DOMAIN}:${PUBLIC_PORT}/login"

printf "\n## 4) NPM/OpenResty (se Docker disponível)\n"
if command -v docker >/dev/null 2>&1; then
  run_or_print "docker ps --format 'table {{.Names}}\\t{{.Ports}}\\t{{.Image}}' | grep -Ei 'npm|nginx|openresty'"
  run_or_print "NPM_CONTAINER=\"\$(docker ps --format '{{.Names}}' | grep -Ei 'npm|nginx|openresty' | head -n1)\"; echo \"NPM_CONTAINER=\$NPM_CONTAINER\""
  run_or_print "NPM_CONTAINER=\"\$(docker ps --format '{{.Names}}' | grep -Ei 'npm|nginx|openresty' | head -n1)\"; docker exec \"\$NPM_CONTAINER\" sh -c 'nginx -T' > /tmp/npm_nginx_dump.txt 2>&1"
  run_or_print "grep -n 'server_name' /tmp/npm_nginx_dump.txt | sed -n '1,220p'"
  run_or_print "grep -n 'proxy_pass' /tmp/npm_nginx_dump.txt | sed -n '1,220p'"
  run_or_print "grep -n 'default_server' /tmp/npm_nginx_dump.txt || true"
  run_or_print "grep -n '${DOMAIN}' /tmp/npm_nginx_dump.txt || true"
else
  echo "docker não encontrado; pulando inspeção de containers NPM/OpenResty."
fi

printf "\n## 5) Comandos de correção mínima sugerida (não executados automaticamente)\n"
cat <<SUGGEST
# Ajuste no NPM (UI):
# - garantir host ${DOMAIN}
# - upstream: http://192.168.3.155:18000
# - dentro do CT 102 o NPM escuta em 443; :${PUBLIC_PORT} é port-forward externo do roteador

# Revalidação final:
curl -k -sSI https://${DOMAIN}/
curl -k -sSI https://${DOMAIN}/login
curl -k -sSI https://${DOMAIN}:${PUBLIC_PORT}/
curl -k -sSI https://${DOMAIN}:${PUBLIC_PORT}/login
curl -k -s https://${DOMAIN}:${PUBLIC_PORT}/ | head -n 40
SUGGEST
