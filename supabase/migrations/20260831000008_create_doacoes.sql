create table if not exists public.doacoes (
  id bigint generated always as identity primary key,
  volume decimal(10,2) not null,
  doador varchar(50) not null,
  telefone varchar(11),
  unidade_medida varchar(10) not null,
  tipo_doacao varchar(50) not null default 'Ração',
  updated_by uuid references public.profiles(id) on delete set null default auth.uid(),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.doacoes enable row level security;

grant select, insert, update, delete on table public.doacoes to authenticated;

drop policy if exists "Authenticated users can read doacoes" on public.doacoes;
create policy "Authenticated users can read doacoes"
  on public.doacoes
  for select
  to authenticated
  using (public.is_active_user());

drop policy if exists "Authenticated users can insert doacoes" on public.doacoes;
create policy "Authenticated users can insert doacoes"
  on public.doacoes
  for insert
  to authenticated
  with check (public.is_active_user());

drop policy if exists "Authenticated users can update doacoes" on public.doacoes;
create policy "Authenticated users can update doacoes"
  on public.doacoes
  for update
  to authenticated
  using (public.is_active_user());

drop policy if exists "Admins can delete doacoes" on public.doacoes;
create policy "Admins can delete doacoes"
  on public.doacoes
  for delete
  to authenticated
  using (public.is_admin());

drop trigger if exists set_doacoes_updated_at on public.doacoes;
create trigger set_doacoes_updated_at
before update on public.doacoes
for each row execute function public.handle_updated_at();

-- Índice para filtragem rápida por tipo de doação
create index if not exists idx_doacoes_tipo_doacao
  on public.doacoes(tipo_doacao);
