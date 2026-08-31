create table if not exists public.pets (
  id bigint generated always as identity primary key,
  status varchar(30) not null,
  nome varchar(30) not null,
  data_nascimento date,
  idade_aproximada_meses int,
  data_castracao date,
  link_documentos text,
  cor_majoritaria varchar(30),
  porte varchar(30),  
  moura varchar(30),
  chip varchar(30),
  rga varchar(30),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.pets enable row level security;

grant select,insert, update on table public.pets to authenticated;

drop policy if exists "Authenticated users can read pets" on public.pets;
create policy "Authenticated users can read pets"
  on public.pets
  for select
  to authenticated
  using (true);

drop policy if exists "Users can insert pets" on public.pets;
create policy "Users can insert pets"
  on public.pets
  for insert
  to authenticated
  with check (true);

drop policy if exists "Users can update pets" on public.pets;
create policy "Users can update pets"
  on public.pets
  for update
  to authenticated
  using (true);

create trigger set_pets_updated_at
before update on public.pets
for each row execute function public.handle_updated_at();