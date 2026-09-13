create table if not exists vacinas(
  id bigint generated always as identity primary key,
  id_pet bigint not null references public.pets(id) on delete cascade,
  id_veterinario bigint references public.veterinarios(id) on delete set null,
  nome_vacina varchar(30) not null,
  data_prevista date not null,
  data_aplicacao date,
  custo numeric(10,2),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.vacinas enable row level security;

grant select,insert, update on table public.vacinas to authenticated;

drop policy if exists "Authenticated users can read vacinas" on public.vacinas;
create policy "Authenticated users can read vacinas"
  on public.vacinas
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert vacinas" on public.vacinas;
create policy "Authenticated users can insert vacinas"
  on public.vacinas
  for insert
  to authenticated
  with check (true);

drop policy if exists "Authenticated users can update vacinas" on public.vacinas;
create policy "Authenticated users can update vacinas"
  on public.vacinas
  for update
  to authenticated
  using (true);

create trigger set_vacinas_updated_at
before update on public.vacinas
for each row execute function public.handle_updated_at();
