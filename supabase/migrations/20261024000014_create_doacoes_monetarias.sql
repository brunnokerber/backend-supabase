create table if not exists public.doacoes_monetarias (
  id bigint generated always as identity primary key,
  valor decimal(10,2) not null check (valor > 0),
  doador varchar(50) not null,
  telefone varchar(11),
  data_doacao date not null default current_date,
  observacoes varchar(255),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.doacoes_monetarias enable row level security;

grant select, insert, update, delete on table public.doacoes_monetarias to authenticated;

drop policy if exists "Authenticated users can read doacoes_monetarias" on public.doacoes_monetarias;
create policy "Authenticated users can read doacoes_monetarias"
  on public.doacoes_monetarias
  for select
  to authenticated
  using (public.is_active_user());

drop policy if exists "Authenticated users can insert doacoes_monetarias" on public.doacoes_monetarias;
create policy "Authenticated users can insert doacoes_monetarias"
  on public.doacoes_monetarias
  for insert
  to authenticated
  with check (public.is_active_user());

drop policy if exists "Authenticated users can update doacoes_monetarias" on public.doacoes_monetarias;
create policy "Authenticated users can update doacoes_monetarias"
  on public.doacoes_monetarias
  for update
  to authenticated
  using (public.is_active_user());

drop policy if exists "Admins can delete doacoes_monetarias" on public.doacoes_monetarias;
create policy "Admins can delete doacoes_monetarias"
  on public.doacoes_monetarias
  for delete
  to authenticated
  using (public.is_admin());

drop trigger if exists set_doacoes_monetarias_updated_at on public.doacoes_monetarias;
create trigger set_doacoes_monetarias_updated_at
before update on public.doacoes_monetarias
for each row execute function public.handle_updated_at();

-- Índices de performance e busca
create index if not exists idx_doacoes_monetarias_data
  on public.doacoes_monetarias(data_doacao desc);

create index if not exists idx_doacoes_monetarias_doador
  on public.doacoes_monetarias(doador);

create index if not exists idx_doacoes_monetarias_doador_trgm
  on public.doacoes_monetarias using gin (doador extensions.gin_trgm_ops);
