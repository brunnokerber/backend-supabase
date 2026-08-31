create table if not exists locais(
  id bigint generated always as identity primary key,
  tipo_local varchar(30) not null,
  contato varchar(50) not null,
  telefone varchar(11) not null,
  local varchar(50) not null,
  bairro varchar(50) not null,
  rua varchar(50) not null,
  numero int not null,
  complemento varchar(30),
  cidade varchar(50) not null,
  estado varchar(2) not null,
  cep varchar(8) not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.locais enable row level security;

grant select,insert, update on table public.locais to authenticated;

drop policy if exists "Authenticated users can read locais" on public.locais;
create policy "Authenticated users can read locais"
  on public.locais
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert locais" on public.locais;
create policy "Authenticated users can insert locais"
  on public.locais
  for insert
  to authenticated
  with check (true);

drop policy if exists "Authenticated users can update locais" on public.locais;
create policy "Authenticated users can update locais"
  on public.locais
  for update
  to authenticated
  using (true);

create trigger set_locais_updated_at
before update on public.locais
for each row execute function public.handle_updated_at();
