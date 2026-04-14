
# Frontend AgentEscala (React + Vite)

Este frontend implementa a interface web do AgentEscala, sistema de gestão de escalas médicas.

## Funcionalidades

- Login protegido por JWT
- Página de calendário de turnos (/calendar)
- Página de trocas (/swaps):
	- Lista trocas reais do usuário logado
	- Permite criar nova solicitação de troca
	- Permite cancelar solicitações pendentes
	- Estados de loading, erro e vazio
- Integração com backend FastAPI via Axios
- Layout responsivo com Tailwind CSS

## Instalação e uso

```bash
cd frontend
npm install
npm run dev
```

Acesse http://localhost:5173 (ou porta configurada pelo Vite).

## Estrutura dos principais arquivos

- `src/pages/swaps_page.jsx` — Página de trocas
- `src/components/swap_card.jsx` — Card de exibição de troca
- `src/components/swap_form.jsx` — Formulário de nova troca

## Observações

- Não depende da etapa E7 para funcionar
- Não altera contratos do backend
- Build validado com `npm run build`
