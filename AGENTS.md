# Diretrizes e Regras do Projeto para Assistentes de IA (AGENTS.md) - Backend Supabase

Este documento estabelece as regras de conduta, padrões arquiteturais, governança de dados e obrigações mandatórias que todo assistente de IA deve cumprir ao propor ou implementar códigos, migrações SQL, Edge Functions, scripts ETL e manutenções neste repositório.

---

## 📌 Contexto do Projeto

- **Projeto:** Sistema de Gestão de Resgates, Acolhimento, Saúde Animal e Doações (*Peludinhos do Vale*)
- **Trabalho Acadêmico:** Trabalho de Conclusão de Curso (TCC) - Engenharia da Computação - Universidade Feevale
- **Stack Principal:** 
  - **BaaS & Banco de Dados:** Supabase CLI, PostgreSQL 15+, PL/pgSQL, Row Level Security (RLS), Triggers, pg_trgm.
  - **Serverless & Autenticação:** Supabase Edge Functions (Deno, TypeScript), Supabase Auth / GoTrue.
  - **Módulo ETL:** Python 3.10+, XML/XLSX Parser, Gerador SQL Idempotente e Carregador Docker.

---

## 🚨 Regra de Ouro: Atualização Contínua e Mandatória de Documentação

> **É IMPRESCINDÍVEL E OBRIGATÓRIO manter toda a documentação do backend sincronizada a cada nova migração, stored procedure, Edge Function ou alteração no ETL.**

Ao concluir qualquer tarefa que envolva mudanças no banco de dados, regras de segurança ou infraestrutura:

1. **Guia Principal do Backend ([README.md](./README.md)):**
   - Atualizar a lista de tabelas do Schema, políticas de RLS, novas RPCs disponíveis e exemplos de endpoints REST.
2. **Documentação do Módulo ETL ([etl/README.md](./etl/README.md)):**
   - Atualizar mapeamentos de colunas, regras de inferência, novos enums ou novos passos de carga no banco de dados.
3. **Resumo da Entrega:**
   - O assistente de IA **sempre deve informar explicitamente ao usuário** quais migrations foram criadas/alteradas, o status do `supabase db reset` e quais seções da documentação foram atualizadas.

---

## 🛠️ Padrões de Código e Arquitetura do Backend

### 1. Migrações PostgreSQL e Banco de Dados
- **Idempotência Obrigatória:** Toda migration deve ser idempotente. Utilize sempre:
  - `CREATE TABLE IF NOT EXISTS ...`
  - `DROP POLICY IF EXISTS "..." ON ...; CREATE POLICY "..." ...`
  - `DROP TRIGGER IF EXISTS ...; CREATE TRIGGER ...`
- **Controle de Timestamps:** Todas as tabelas devem possuir `created_at` e `updated_at` com `TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())` e trigger automático chamando `public.handle_updated_at()`.
- **Row Level Security (RLS) Mandatório:** 100% das tabelas públicas devem ter RLS ativo (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`) com `GRANT` explícito e políticas de segurança configuradas.
- **Funções de Segurança Centrais:**
  - `public.is_active_user()`: Valida se o usuário autenticado está ativo e não deletado (`ativo = true AND deleted_at IS NULL`).
  - `public.is_admin()`: Valida se o usuário autenticado possui `role = 'admin'` ativo ou acesso de sistema (`service_role`, `postgres`).

### 2. Integridade Referencial e Políticas de Exclusão (`DELETE`)
- **Tabelas Primárias (`pets`, `veterinarios`, `locais`, `doacoes`, `direcionamento_doacoes`, `entradas`, `profiles`):**
  - **NÃO** devem possuir política de `DELETE` aberta para usuários comuns para evitar registros órfãos ou exclusões em cascata indesejadas.
- **Tabelas Intermediárias / Prontuário (`vacinas`, `consultas_exames`, `pets_locais`, `voluntarios`):**
  - A permissão de `DELETE` deve ser **estritamente restrita a Administradores** (`USING (public.is_admin())`) para viabilizar correções de lançamentos incorretos.

### 3. Procedimentos Atômicos (Stored Procedures / RPCs)
- **Operações Multi-Tabela:** Sempre que uma operação no frontend envolver salvar ou atualizar mais de uma entidade (ex: `pets` + `entradas`), crie e utilize **Stored Procedures (RPCs)** transacionais com `SECURITY DEFINER` (ex: `create_pet_com_entrada`, `update_pet_com_entrada`), garantindo rollback atômico e evitando chamadas HTTP sequenciais.

### 4. Estratégia de Índices e Performance
- **Chaves Estrangeiras (FKs):** Toda coluna que referencia outra tabela (`id_pet`, `id_veterinario`, `id_local`, `id_usuario`) **deve** possuir índice B-Tree criado para evitar *Full Table Scan* em JOINs.
- **Busca Textual:** Utilize a extensão `pg_trgm` com índices `GIN` (`extensions.gin_trgm_ops`) para acelerar consultas de substring (`ILIKE '%termo%'`) em nomes e descrições.
- **Prontuário Ordenado:** Crie índices compostos cobrindo chave estrangeira e data de ordenação (ex: `(id_pet, data_aplicacao DESC NULLS LAST)`).

### 5. Edge Functions (Deno / TypeScript)
- **CORS e Preflight:** Sempre tratar requisições `OPTIONS` retornando os headers de CORS.
- **Padronização de Resposta:** Utilizar funções auxiliares de resposta JSON (`successResponse` e `errorResponse` com status HTTP adequado).
- **Validação de Token e Admin:** Extrair e validar o token Bearer do cabeçalho `Authorization` via `adminClient.auth.getUser(token)` e validar role de admin antes de executar ações privilegiadas.

### 6. Módulo de ETL (Python)
- **Conformidade com o Frontend:** Manter sincronizados os enums e regras de negócio de `models.py` e `transformer.py` com o Frontend Angular (ex: cálculo de senioridade, tipos de pet, vacinas padronizadas).
- **Isolamento de Seeds:**
  - `supabase/seed.sql`: Contém **apenas** a criação do usuário administrador inicial (`admin@admin.com` / `Admin@123`).
  - `etl/data/output/seed_peludinhos_etl.sql`: Contém os dados legados processados pelo pipeline ETL, aplicados via `python -m etl.main --load-db`.

---

## 📋 Checklist Obrigatório de Finalização de Tarefa

Antes de considerar uma tarefa concluída no backend, o assistente de IA deve validar:
- [ ] O comando `npx supabase db reset` executa sem erros e aplica todas as migrations?
- [ ] O pipeline ETL (`python -m etl.main --load-db`) executa e popula os dados com sucesso?
- [ ] Novas tabelas possuem RLS ativado, triggers de `updated_at` e índices adequados?
- [ ] A documentação no [README.md](./README.md) ou [etl/README.md](./etl/README.md) foi devidamente atualizada?
- [ ] Foi apresentado ao usuário um resumo claro das alterações realizadas?
