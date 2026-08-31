create table if not exists entradas(
  id bigint generated always as identity primary key,
  id_usuario uuid not null references auth.users(id) on delete cascade,
  id_pet bigint not null references public.pets(id) on delete cascade,
  local_origem varchar(50) not null,
  data_entrada date not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.entradas enable row level security;

grant select,insert, update on table public.entradas to authenticated;

drop policy if exists "Authenticated users can read entradas" on public.entradas;
create policy "Authenticated users can read entradas"
  on public.entradas
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert entradas" on public.entradas;
create policy "Authenticated users can insert entradas"
  on public.entradas
  for insert
  to authenticated
  with check (true);

drop policy if exists "Authenticated users can update entradas" on public.entradas;
create policy "Authenticated users can update entradas"
  on public.entradas
  for update
  to authenticated
  using (true);

create trigger set_entradas_updated_at
before update on public.entradas
for each row
execute function public.handle_updated_at();
