-- ==============================================================================
-- Migration: Criação da Tabela de Despesas Gerais da Instituição (public.despesas)
-- e View Consolidada de Fluxo de Caixa (public.vw_fluxo_caixa)
-- ==============================================================================

create table if not exists public.despesas (
  id bigint generated always as identity primary key,
  descricao varchar(100) not null,
  categoria varchar(50) not null check (
    categoria in (
      'Alimentação / Ração',
      'Medicamentos & Insumos Gerais',
      'Higiene & Limpeza',
      'Transporte & Resgate',
      'Infraestrutura & Sede',
      'Serviços Veterinários Avulsos',
      'Administrativo & Operacional',
      'Outro'
    )
  ),
  valor decimal(10,2) not null check (valor > 0),
  data_despesa date not null default current_date,
  favorecido varchar(100) not null,
  telefone varchar(11),
  observacoes varchar(255),
  id_pet bigint references public.pets(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  updated_by uuid references public.profiles(id) on delete set null default auth.uid()
);

-- Comentários de Governança e Dicionário de Dados
comment on table public.despesas is 'Registro de despesas e saídas financeiras institucionais e operacionais da ONG.';
comment on column public.despesas.categoria is 'Classificação de despesa para geração de gráficos e balanço orçamentário.';
comment on column public.despesas.favorecido is 'Nome do fornecedor, clínica, estabelecimento ou prestador de serviço favorecido.';
comment on column public.despesas.id_pet is 'Vínculo opcional com um animal resgatado caso o gasto tenha sido direcionado especificamente a ele.';

-- ==============================================================================
-- 1. Políticas de Segurança (Row Level Security - RLS) e Permissões
-- ==============================================================================
alter table public.despesas enable row level security;

grant select, insert, update, delete on table public.despesas to authenticated;

-- Leitura: Qualquer usuário autenticado e ativo
drop policy if exists "Authenticated users can read despesas" on public.despesas;
create policy "Authenticated users can read despesas"
  on public.despesas
  for select
  to authenticated
  using (public.is_active_user());

-- Inserção: Qualquer usuário autenticado e ativo
drop policy if exists "Authenticated users can insert despesas" on public.despesas;
create policy "Authenticated users can insert despesas"
  on public.despesas
  for insert
  to authenticated
  with check (public.is_active_user());

-- Edição: Qualquer usuário autenticado e ativo
drop policy if exists "Authenticated users can update despesas" on public.despesas;
create policy "Authenticated users can update despesas"
  on public.despesas
  for update
  to authenticated
  using (public.is_active_user())
  with check (public.is_active_user());

-- Exclusão: EXCLUSIVA PARA ADMINISTRADORES (Regra estrita de auditoria contábil)
drop policy if exists "Admins can delete despesas" on public.despesas;
create policy "Admins can delete despesas"
  on public.despesas
  for delete
  to authenticated
  using (public.is_admin());

-- ==============================================================================
-- 2. Gatilho de Auditoria Temporal e Autoria (updated_at + updated_by)
-- ==============================================================================
drop trigger if exists set_despesas_updated_at on public.despesas;
create trigger set_despesas_updated_at
  before update on public.despesas
  for each row
  execute function public.handle_updated_at();

-- ==============================================================================
-- 3. Índices de Otimização e Performance
-- ==============================================================================
-- Aceleração de filtros por período temporal no painel financeiro (B-Tree)
create index if not exists idx_despesas_data
  on public.despesas(data_despesa desc);

-- Agrupamento rápido de saídas por categoria em gráficos (B-Tree)
create index if not exists idx_despesas_categoria
  on public.despesas(categoria);

-- Busca textual eficiente por nome do favorecido/fornecedor (Trigram GIN)
create index if not exists idx_despesas_favorecido_trgm
  on public.despesas using gin (favorecido extensions.gin_trgm_ops);

-- Índice de Foreign Key para joins com pets
create index if not exists idx_despesas_id_pet
  on public.despesas(id_pet);

-- Índice de Foreign Key para joins com public.profiles (Auditoria)
create index if not exists idx_despesas_updated_by
  on public.despesas(updated_by);

-- ==============================================================================
-- 4. View Consolidada de Fluxo de Caixa (public.vw_fluxo_caixa)
-- ==============================================================================
create or replace view public.vw_fluxo_caixa
with (security_invoker = true) as
-- 1. Entradas (Doações Monetárias)
select 
  'Entrada'::varchar(10) as tipo_movimentacao,
  'Doação Monetária'::varchar(50) as categoria,
  valor,
  data_doacao as data_movimentacao,
  doador::varchar(100) as pessoa_referencia,
  observacoes::text as observacoes,
  null::bigint as id_pet,
  created_at
from public.doacoes_monetarias

union all

-- 2. Saídas Gerais (Despesas Institucionais)
select 
  'Saída'::varchar(10) as tipo_movimentacao,
  categoria,
  valor,
  data_despesa as data_movimentacao,
  favorecido::varchar(100) as pessoa_referencia,
  observacoes::text as observacoes,
  id_pet,
  created_at
from public.despesas

union all

-- 3. Saídas Clínicas (Consultas, Cirurgias e Exames dos Pets)
select 
  'Saída'::varchar(10) as tipo_movimentacao,
  coalesce(tipo_operacao, 'Procedimento Clínico')::varchar(50) as categoria,
  custo as valor,
  data_realizacao as data_movimentacao,
  'Clínica / Procedimento Pet'::varchar(100) as pessoa_referencia,
  operacao_medicamento::text as observacoes,
  id_pet,
  created_at
from public.consultas_exames
where custo is not null and custo > 0

union all

-- 4. Saídas Preventivas (Vacinas Aplicadas)
select 
  'Saída'::varchar(10) as tipo_movimentacao,
  'Vacinação Preventiva'::varchar(50) as categoria,
  custo as valor,
  coalesce(data_aplicacao, data_prevista) as data_movimentacao,
  nome_vacina::varchar(100) as pessoa_referencia,
  'Aplicação vacinal'::text as observacoes,
  id_pet,
  created_at
from public.vacinas
where custo is not null and custo > 0

union all

-- 5. Saídas de Hospedagem / Estadia (Auxílio de Custo para Lares Temporários)
select 
  'Saída'::varchar(10) as tipo_movimentacao,
  'Auxílio Lar Temporário'::varchar(50) as categoria,
  pl.valor_auxilio as valor,
  pl.data_saida as data_movimentacao,
  coalesce(l.local, 'Lar Temporário')::varchar(100) as pessoa_referencia,
  coalesce(nullif(trim(pl.obs), ''), nullif(trim(pl.motivo_saida), ''), 'Auxílio de custo de lar temporário')::text as observacoes,
  pl.id_pet,
  pl.created_at
from public.pets_locais pl
left join public.locais l on l.id = pl.id_local
where pl.valor_auxilio is not null and pl.valor_auxilio > 0;

-- Índice para otimizar busca de auxílios financeiros em estadias
create index if not exists idx_pets_locais_valor_auxilio
  on public.pets_locais(valor_auxilio)
  where valor_auxilio is not null and valor_auxilio > 0;

comment on view public.vw_fluxo_caixa is 'Visão consolidada do fluxo financeiro: entradas (doações monetárias) e saídas (despesas institucionais, custos clínicos, vacinas e auxílios de custo de lares temporários).';

grant select on public.vw_fluxo_caixa to authenticated;
