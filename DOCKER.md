# Docker Setup

Roda o projeto completo (Postgres, backend FastAPI, frontend Next.js) com um comando.

## Quickstart

```bash
# Build e roda tudo
docker-compose up

# Pronto para testar
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/api/health
# Banco:    localhost:5433 (usuario: emporio, senha: emporio)
```

## Primeiro uso

1. **Criar usuário** (antes ou depois, via script local):
   ```bash
   # Fora do Docker (requer frontend/.env.local configurado)
   cd frontend
   CREATE_USER_PASSWORD=SenhaForte123 pnpm tsx scripts/create-user.ts adm
   ```

   Ou pela CLI do Docker:
   ```bash
   docker-compose exec frontend pnpm tsx scripts/create-user.ts adm
   # Digite a senha quando pedir
   ```

2. **Login em http://localhost:3000**
   - Username: `adm`
   - Password: aquela que você configurou

3. **Chat funciona**
   - Backend fake (sem custo de API real) por padrão
   - Rota do backend: `/api/chat`

## Variáveis de ambiente

Criadas automaticamente via `docker-compose.yml` com defaults sensatos:

- `BACKEND_URL`: `http://backend:8000` (interno, Docker)
- `DATABASE_URL`: `postgresql://emporio:emporio@db:5432/emporio`
- `SERVICE_JWT_SECRET`: `dev-secret-at-least-32-bytes-long-ok` (dev mode)
- `LLM_PROVIDER`: `fake` (sem custo)

Para usar em desenvolvimento local (não Docker), copie `frontend/.env.example` → `frontend/.env.local` e `backend/.env.example` → `backend/.env`, ajustando `DATABASE_URL` pra `localhost:5433` e rodando os serviços manualmente.

## Produção (Vercel)

Quando deployar na Vercel:

1. Configure variáveis de ambiente no painel Vercel:
   - `BACKEND_URL`: URL do seu backend (ex: outro deploy, Railway, etc)
   - `AUTH_SECRET`: 32+ caracteres aleatórios
   - `SERVICE_JWT_SECRET`: **mesmo valor do backend**, 32+ caracteres
   - `NEXT_PUBLIC_*`: qualquer var que o frontend precise

2. Backend vai precisar estar deployado em algum lugar (Railway, seu servidor, etc).

3. Banco Neon já está integrado (via Vercel Postgres add-on).

## Troubleshooting

**Porta 5433/3000/8000 já em uso:**
```bash
docker-compose down  # Para tudo
lsof -ti:5433 | xargs kill -9  # Mata o processo
docker-compose up    # Roda de novo
```

**Banco sem dados:**
```bash
docker-compose down -v  # Remove volume (banco vazio)
docker-compose up       # Roda do zero
```

**Build lento ou falha:**
```bash
docker-compose build --no-cache
docker-compose up
```
