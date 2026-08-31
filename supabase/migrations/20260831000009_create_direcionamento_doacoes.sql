create table if not exists direcionamento_doacoes(
  id bigint generated always as identity primary key,
  id_local bigint not null references public.locais(id) on delete cascade,
  id_doacao bigint not null references public.doacoes(id) on delete cascade,
  volume decimal(10,2) not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.direcionamento_doacoes enable row level security;

grant select,insert, update on table public.direcionamento_doacoes to authenticated;

drop policy if exists "Authenticated users can read direcionamento_doacoes" on public.direcionamento_doacoes;
create policy "Authenticated users can read direcionamento_doacoes"
  on public.direcionamento_doacoes
  for select
  to authenticated
  using (true);

drop policy if exists "Authenticated users can insert direcionamento_doacoes" on public.direcionamento_doacoes;
create policy "Authenticated users can insert direcionamento_doacoes"
  on public.direcionamento_doacoes
  for insert
  to authenticated
   with check (true);

drop policy if exists "Authenticated users can update direcionamento_doacoes" on public.direcionamento_doacoes;
create policy "Authenticated users can update direcionamento_doacoes"
  on public.direcionamento_doacoes
  for update
  to authenticated
  using (true);

create trigger set_direcionamento_doacoes_updated_at
before update on public.direcionamento_doacoes
for each row execute function public.handle_updated_at();
