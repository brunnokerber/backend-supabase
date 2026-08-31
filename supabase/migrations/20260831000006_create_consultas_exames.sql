create table if not exists consultas_exames(
  id bigint generated always as identity primary key,
  id_pet bigint not null references public.pets(id) on delete cascade,
  id_veterinario bigint references public.veterinarios(id) on delete set null,
  operacao_medicamento varchar(300) not null,
  data_realizacao date not null,
  custo decimal(10,2),
  tipo_operacao varchar(30) not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.consultas_exames enable row level security;

grant select,insert, update on table public.consultas_exames to authenticated;

drop policy if exists "Authenticated users can read consultas_exames" on public.consultas_exames;
create policy "Authenticated users can read consultas_exames"
  on public.consultas_exames
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert consultas_exames" on public.consultas_exames;
create policy "Authenticated users can insert consultas_exames"
  on public.consultas_exames
  for insert
  to authenticated
  with check (true);

drop policy if exists "Authenticated users can update consultas_exames" on public.consultas_exames;
create policy "Authenticated users can update consultas_exames"
  on public.consultas_exames
  for update
  to authenticated
  using (true);

create trigger set_consultas_exames_updated_at
before update on public.consultas_exames
for each row execute function public.handle_updated_at();
