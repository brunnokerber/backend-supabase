create table if not exists pets_locais(
  id bigint generated always as identity primary key, 
  id_local bigint not null references public.locais(id) on delete cascade,
  id_pet bigint not null references public.pets(id) on delete cascade,
  motivo_saida varchar(50),
  data_reentrada date not  null,
  data_saida date,
  valor_auxilio decimal(10,2),
  obs varchar(200),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.pets_locais enable row level security;

grant select,insert, update on table public.pets_locais to authenticated;

drop policy if exists "Authenticated users can read pets_locais" on public.pets_locais;
create policy "Authenticated users can read pets_locais"
  on public.pets_locais
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert pets_locais" on public.pets_locais;
create policy "Authenticated users can insert pets_locais"
  on public.pets_locais
  for insert
  to authenticated
  with check (true);

drop policy if exists "Authenticated users can update pets_locais" on public.pets_locais;
create policy "Authenticated users can update pets_locais"
  on public.pets_locais
  for update
  to authenticated
  using (true);

create trigger set_pets_locais_updated_at
before update on public.pets_locais
for each row execute function public.handle_updated_at();
