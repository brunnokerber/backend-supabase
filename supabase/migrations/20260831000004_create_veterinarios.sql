create table if not exists veterinarios(
  id bigint generated always as identity primary key,
  nome varchar(30) not null,
  telefone varchar(11) not null,
  crvet varchar(30) not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.veterinarios enable row level security;

grant select,insert, update on table public.veterinarios to authenticated;

drop policy if exists "Authenticated users can read veterinarios" on public.veterinarios;
create policy "Authenticated users can read veterinarios"
  on public.veterinarios
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert veterinarios" on public.veterinarios;
create policy "Authenticated users can insert veterinarios"
  on public.veterinarios
  for insert
  to authenticated
  with check (true);

drop policy if exists "Authenticated users can update veterinarios" on public.veterinarios;
create policy "Authenticated users can update veterinarios"
  on public.veterinarios
  for update
  to authenticated
  using (true);

create trigger set_veterinarios_updated_at
before update on public.veterinarios
for each row execute function public.handle_updated_at();
