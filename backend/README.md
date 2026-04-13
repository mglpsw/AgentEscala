# Backend do AgentEscala

Este é o serviço backend do sistema de gestão e trocas de turnos AgentEscala.

## Estrutura

- `main.py` - Ponto de entrada da aplicação FastAPI
- `config/` - Configurações e conexão com o banco
- `models/` - Modelos de banco de dados em SQLAlchemy
- `services/` - Camada de regras de negócio
- `api/` - Endpoints REST da aplicação
- `utils/` - Utilitários (exportadores Excel e ICS)

## Execução

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
