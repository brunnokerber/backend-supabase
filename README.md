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
   - Cadastro dos animais resgatados (status, nome, datas, porte, pelagem, chip, rga, link_documentos, foto_url), criação do bucket privado `pets` no Supabase Storage (limite de 256 KB, restrição MIME para imagens) e políticas de RLS para acesso autenticado.
4. **`entradas`** (`20260831000003_create_entradas.sql`):
   - Registro de entrada do pet na organização/abrigo, vinculado ao usuário responsável (`auth.users`) e ao animal. Contém as RPCs transacionais atômicas `create_pet_com_entrada` e `update_pet_com_entrada`.
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
12. **`voluntarios`** (`20261008000011_create_voluntarios.sql`):
    - Cadastro de voluntários da organização (nome, e-mail, telefone, dias da semana, turnos e observações). RLS restrito a administradores.
13. **`indexes_and_search`** (`20261008000012_create_indexes_and_search.sql`):
    - Extensão `pg_trgm`, índices em todas as Foreign Keys (FKs), ordenação de prontuários e índices GIN para busca textual de alta performance.
14. **`adotar_pet`** (`20261014000013_create_adotar_pet_rpc.sql`):
    - Stored procedure transacional atômica para o fluxo de adoção de pets: validação de status `Disponível` (com lock pessimista `FOR UPDATE`), atualização de status para `Adotado`, inserção no histórico de estadias (`pets_locais`) e retorno estruturado com tratamento de exceções amigáveis.

---

## Stored Procedures (RPCs)
- **`create_pet_com_entrada(p_pet_data, p_entrada_data)`**: Criação atômica de Pet (incluindo `foto_url`, identificadores e documentos) e registro de Entrada em uma única transação (`SECURITY DEFINER`).
- **`update_pet_com_entrada(p_pet_id, p_pet_data, p_entrada_data)`**: Atualização conjunta de dados cadastrais do animal (incluindo `foto_url`) e de entrada com consistência transacional.
- **`adotar_pet(p_pet_id, p_pet_local_data)`**: Processamento atômico e transacional do fluxo de adoção de um animal.
  - **Segurança:** Acesso restrito a usuários ativos e autenticados (`public.is_active_user()`).
  - **Regra de Negócio:** Permite a adoção exclusivamente de pets com status `'Disponível'`. Caso o pet esteja com qualquer outro status (ex: `'Adotado'`, `'Em Tratamento'`, `'Quarentena'`, `'Óbito'`), aborta a transação com uma mensagem de erro amigável contextualizada.
  - **Atomicidade e Concorrência:** Utiliza lock pessimista (`FOR UPDATE`) para evitar condições de corrida. Altera o status do animal para `'Adotado'` e insere imediatamente o registro em `public.pets_locais` com o local de destino, data de saída, motivo (default `'Adoção'`), observações e valor de auxílio.
  - **Exemplo de Chamada no Frontend / Angular:**
    ```typescript
    const { data, error } = await supabase.rpc('adotar_pet', {
      p_pet_id: 12,
      p_pet_local_data: {
        id_local: 3,
        data_saida: '2026-10-14',
        motivo_saida: 'Adoção Definitiva',
        obs: 'Adotado com termo de responsabilidade assinado'
      }
    });
    ```

---

## Armazenamento de Imagens (Supabase Storage)

- **Bucket:** `pets` (privado, `public = false`).
- **Tamanho Máximo por Arquivo:** `256 KB` (`262144` bytes).
- **Tipos de Arquivo Permitidos:** `image/jpeg`, `image/png`, `image/webp`.
- **Políticas de Acesso (RLS):**
  - `SELECT`: Apenas usuários autenticados e ativos (`public.is_active_user()`).
  - `INSERT` / `UPDATE`: Usuários autenticados e ativos (`public.is_active_user()`).
  - `DELETE`: Exclusivo para administradores (`public.is_admin()`).
- **Consumo no Frontend:**
  - O upload gera o caminho do arquivo (ex: `avatars/pet-123.webp`), que é persistido via RPC em `pets.foto_url`.
  - Na tela de detalhes do pet, a URL assinada é gerada com:
    ```typescript
    const { data: { signedUrl } } = await supabase.storage
      .from('pets')
      .createSignedUrl(pet.foto_url, 3600);
    ```

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
- **Política de Senhas Fortes (`config.toml`):**
  - Mínimo de 8 caracteres (`minimum_password_length = 8`).
  - Complexidade obrigatória (`password_requirements = "lower_upper_letters_digits_symbols"`): exige letras maiúsculas, minúsculas, números e caracteres especiais.
- **Governança de Acesso e Sessão (`config.toml`):**
  - **Inscrição Pública Desativada:** Tanto em `[auth]` quanto em `[auth.email]`, o cadastro direto está fechado (`enable_signup = false`). Novos voluntários só entram via convite disparado por Administradores (Edge Function `invite-user`).
  - **Reautenticação em Alteração de Senha:** `secure_password_change = true`, exigindo sessão recente para atualizar a credencial.
  - **Controle de Inatividade de Sessão:** `timebox = "24h"` (logout forçado após 24h) e `inactivity_timeout = "8h"` (logout automático por ociosidade).
- **Usuário Administrador Padrão (Ambiente de Desenvolvimento / `seed.sql`):**
  - **E-mail:** `admin@admin.com`
  - **Senha:** `Admin@123`
  - **Role:** `admin`

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
- `POST /rest/v1/rpc/adotar_pet` (Adoção atômica com validação de status)
- `POST /rest/v1/rpc/create_pet_com_entrada` (Cadastro atômico de Pet e Entrada)
- `POST /rest/v1/rpc/update_pet_com_entrada` (Edição atômica de Pet e Entrada)

---

## Integração Contínua (CI/CD)

- **`pull_request -> main`:** Valida as migrations localmente executando `supabase start` e `supabase db reset`.
- **`push -> main`:** Aplica as novas migrations no projeto Supabase em produção via `supabase db push --linked`.

### Secrets configurados no GitHub Actions:
- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_DB_PASSWORD`

