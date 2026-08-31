create table if not exists doacoes(
  id bigint generated always as identity primary key,
  volume decimal(10,2) not null,
  doador varchar(50) not null,
  telefone varchar(11),
  unidade_medida varchar(10) not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.doacoes enable row level security;

grant select,insert, update on table public.doacoes to authenticated;

drop policy if exists "Authenticated users can read doacoes" on public.doacoes;
create policy "Authenticated users can read doacoes"
  on public.doacoes
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert doacoes" on public.doacoes;
create policy "Authenticated users can insert doacoes"
  on public.doacoes
  for insert
  to authenticated
  with check (true);

drop policy if exists "Authenticated users can update doacoes" on public.doacoes;
create policy "Authenticated users can update doacoes"
  on public.doacoes
  for update
  to authenticated
  using (true);

create trigger set_doacoes_updated_at
before update on public.doacoes
for each row execute function public.handle_updated_at();
