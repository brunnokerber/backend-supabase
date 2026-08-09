# Backend Supabase

Projeto mínimo de backend com Supabase para testar consulta direta em tabela com RLS e autenticação.

## O que foi criado

- `supabase/config.toml`: configuração base do projeto local.
- `supabase/migrations/20260809000000_create_hello_world_messages.sql`: tabela `hello_world_messages` com RLS.
- `supabase/migrations/20260809000001_create_profiles_and_roles.sql`: perfis de usuário e roles `user`/`admin`.
- `supabase/seed.sql`: insere a linha inicial de hello world.

## Como rodar localmente

1. Inicie a stack do Supabase:

```bash
supabase start
```

2. Aplique a migração e o seed no banco local:

```bash
supabase db reset
```

## Fluxo de autenticação

1. Um admin cria o usuário pelo Studio ou pela Admin API do Supabase.
2. Um registro em `public.profiles` será criado automaticamente para esse usuário com role `user`.
3. O usuário faz login e copia o `access_token` retornado.
4. Use esse token para consultar a tabela via REST API.

## Roles

- `user`: papel padrão de qualquer usuário autenticado.
- `admin`: papel para contas administrativas do app.

Você pode promover um usuário para `admin` atualizando a coluna `role` em `public.profiles` via Studio ou SQL.

## Exemplo de consulta no Insomnia

Endpoint:

```text
http://127.0.0.1:54321/rest/v1/hello_world_messages?select=*
```

Headers:

- `apikey: <SUA_ANON_KEY>`
- `Authorization: Bearer <ACCESS_TOKEN_DO_USUARIO>`

Exemplo de resposta:

```json
{
  "id": 1,
  "message": "Hello, world from Supabase SQL!",
  "created_at": "2026-08-09T00:00:00Z"
}
```

Se quiser testar o login via `curl`, o endpoint é:

```bash
curl -i -X POST "http://127.0.0.1:54321/auth/v1/token?grant_type=password" \
  -H "apikey: <SUA_ANON_KEY>" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"teste@exemplo.com\",\"password\":\"12345678\"}"
```

Depois, use o `access_token` retornado no header `Authorization` da consulta REST.

## Consultar perfil

Endpoint:

```text
http://127.0.0.1:54321/rest/v1/profiles?select=*
```

Com RLS ativo, um usuário autenticado só enxerga o próprio perfil. Um admin enxerga todos os perfis.

## CI/CD

- `pull_request -> main`: roda a validação local com `supabase start` e `supabase db reset`.
- `push -> main`: aplica as migrations no Supabase cloud com `supabase db push --linked`.

Secrets necessários no GitHub:

- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_DB_PASSWORD`

Se você adicionar Edge Functions no futuro, o deploy delas pode entrar no mesmo fluxo da `main`.
