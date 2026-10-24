create table if not exists public.voluntarios (
  id bigint generated always as identity primary key,
  nome varchar(50) not null,
  email varchar(300),
  telefone varchar(11) not null,
  dias_semana text[] default '{}',
  turnos text[] default '{}',
  observacoes text,
  updated_by uuid references public.profiles(id) on delete set null default auth.uid(),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.voluntarios enable row level security;

grant select, insert, update, delete on table public.voluntarios to authenticated;

drop policy if exists "Admins can read voluntarios" on public.voluntarios;
create policy "Admins can read voluntarios"
  on public.voluntarios
  for select
  to authenticated
  using (public.is_admin());

drop policy if exists "Admins can insert voluntarios" on public.voluntarios;
create policy "Admins can insert voluntarios"
  on public.voluntarios
  for insert
  to authenticated
  with check (public.is_admin());

drop policy if exists "Admins can update voluntarios" on public.voluntarios;
create policy "Admins can update voluntarios"
  on public.voluntarios
  for update
  to authenticated
  using (public.is_admin());

drop policy if exists "Admins can delete voluntarios" on public.voluntarios;
create policy "Admins can delete voluntarios"
  on public.voluntarios
  for delete
  to authenticated
  using (public.is_admin());

drop trigger if exists set_voluntarios_updated_at on public.voluntarios;
create trigger set_voluntarios_updated_at
before update on public.voluntarios
for each row execute function public.handle_updated_at();
