# Backend Supabase - Gestão de Resgate, Acolhimento e Doações

Backend desenvolvido em **Supabase (PostgreSQL)** para o sistema de gestão de resgate de animais, controle de saúde/veterinário, lares temporários e direcionamento de doações.

---

## Estrutura do Banco de Dados (Schema)

O banco é versionado através de **migrations SQL** (`supabase/migrations/`) e conta com Row Level Security (RLS) habilitado em todas as tabelas:

1. **`profiles`** (`20260809000000_create_profiles_and_roles.sql`):
   - Perfis de usuários vinculados ao `auth.users` via trigger automático, com controle de papéis (`app_role`: `'user'`, `'admin'`).
2. **`handle_updated_at`** (`20260831000001_create_update_at_function.sql`):
   - Função utilitária global para atualização automática do campo `updated_at` via triggers.
3. **`pets`** (`20260831000002_create_pets.sql`):
   - Cadastro dos animais resgatados (status, nome, datas, porte, pelagem, chip, rga, etc.).
4. **`entradas`** (`20260831000003_create_entradas.sql`):
   - Registro de entrada do pet na organização/abrigo, vinculado ao usuário responsável (`auth.users`) e ao animal.
5. **`veterinarios`** (`20260831000004_create_veterinarios.sql`):
   - Cadastro de médicos veterinários e clínicas parceiras (nome, telefone, CRMV).
6. **`vacinas`** (`20260831000005_create_vacinas.sql`):
   - Controle do calendário vacinal dos pets (prevista, aplicação, veterinário responsável).
7. **`consultas_exames`** (`20260831000006_create_consultas_exames.sql`):
   - Histórico clínico do pet (consultas, procedimentos cirúrgicos, exames, medicamentos, custos).
8. **`locais`** (`20260831000007_create_locais.sql`):
   - Cadastro de lares temporários, abrigos e pontos de apoio (endereço, contato, responsável).
9. **`doacoes`** (`20260831000008_create_doacoes.sql`):
   - Registro de doações recebidas (ração, medicamentos, insumos, volume e unidade de medida).
10. **`direcionamento_doacoes`** (`20260831000009_create_direcionamento_doacoes.sql`):
    - Controle de distribuição de doações para os locais/lares temporários.
11. **`pets_locais`** (`20260831000010_create_pets_locais.sql`):
    - Histórico de hospedagem e permanência dos pets nos locais/lares temporários com controle de auxílio financeiro.

---

## Como Rodar Localmente

### Pré-requisitos
- [Docker Desktop](https://www.docker.com/) instalado e em execução.
- [Supabase CLI](https://supabase.com/docs/guides/cli) instalado.

### 1. Iniciar a stack local do Supabase
```bash
supabase start
```

### 2. Aplicar todas as migrations no banco local
```bash
supabase db reset
```

---

## Autenticação e Controle de Acesso (RLS)

- **Criação de Usuários:** Ao criar um usuário no Supabase Auth, uma linha correspondente é inserida automaticamente na tabela `public.profiles` com papel `user`.
- **Roles:**
  - `user`: Usuário autenticado padrão.
  - `admin`: Usuário com privilégios administrativos. Pode ser promovido alterando a coluna `role` em `public.profiles`.
- **Row Level Security (RLS):** Ativo em todas as tabelas, garantindo que apenas requisições autenticadas possam consultar ou manipular dados.

---

## Consumo da API REST

Após rodar `supabase start`, os endpoints REST estarão disponíveis em `http://127.0.0.1:54321/rest/v1/`.

### Headers obrigatórios nas requisições:
```text
apikey: <SUA_ANON_KEY>
Authorization: Bearer <ACCESS_TOKEN_DO_USUARIO>
```

### Exemplos de Endpoints:
- `GET /rest/v1/pets?select=*`
- `GET /rest/v1/pets?select=*,entradas(*),vacinas(*),consultas_exames(*)`
- `GET /rest/v1/locais?select=*,pets_locais(*,pets(*))`
- `GET /rest/v1/doacoes?select=*,direcionamento_doacoes(*,locais(*))`

---

## Integração Contínua (CI/CD)

- **`pull_request -> main`:** Valida as migrations localmente executando `supabase start` e `supabase db reset`.
- **`push -> main`:** Aplica as novas migrations no projeto Supabase em produção via `supabase db push --linked`.

### Secrets configurados no GitHub Actions:
- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_DB_PASSWORD`

