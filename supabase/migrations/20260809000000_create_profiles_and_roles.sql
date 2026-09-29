-- 1. Tipo Enum para papéis de acesso
do $$
begin
  if not exists (select 1 from pg_type where typname = 'app_role') then
    create type public.app_role as enum ('user', 'admin');
  end if;
end$$;

-- 2. Tabela de Perfis de Usuário (com a coluna email, ativo e deleted_at)
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  role public.app_role not null default 'user',
  ativo boolean not null default true,
  deleted_at timestamptz default null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- 3. Função e Trigger para atualizar updated_at automaticamente
create or replace function public.set_profiles_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists set_profiles_updated_at on public.profiles;
create trigger set_profiles_updated_at
before update on public.profiles
for each row
execute function public.set_profiles_updated_at();

-- 4. Função auxiliar para verificar se quem está logado é admin
create or replace function public.is_admin()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select
    -- Execuções diretas no banco (SQL Editor do Dashboard, migrations, psql)
    current_user in ('postgres', 'supabase_admin', 'service_role')
    -- Requisições autenticadas com service_role key (Edge Functions / Backend)
    or (auth.role() = 'service_role')
    -- Usuário autenticado na aplicação com perfil admin ativo
    or (
      auth.uid() is not null
      and exists (
        select 1
        from public.profiles
        where id = auth.uid()
          and role = 'admin'
          and ativo = true
      )
    );
$$;

-- 5. Trigger que sincroniza o perfil quando um novo usuário é cadastrado/convidado
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  assigned_role public.app_role;
begin
  begin
    assigned_role := coalesce((new.raw_user_meta_data->>'role')::public.app_role, 'user'::public.app_role);
  exception when others then
    assigned_role := 'user'::public.app_role;
  end;

  insert into public.profiles (id, email, role, ativo, created_at, updated_at)
  values (
    new.id,
    new.email,
    assigned_role,
    true,
    timezone('utc', now()),
    timezone('utc', now())
  )
  on conflict (id) do update
  set
    email = excluded.email,
    updated_at = timezone('utc', now());

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

-- 6. Habilita RLS (Row Level Security)
alter table public.profiles enable row level security;

grant select, update on table public.profiles to authenticated;
grant select, update, insert on table public.profiles to service_role;

create or replace function public.current_user_role()
returns public.app_role
language sql
stable
security definer
set search_path = public
as $$
  select role
  from public.profiles
  where id = auth.uid()
  limit 1
$$;

-- Leitura: Usuário vê a si mesmo; Admins veem todos
drop policy if exists "Leitura de perfis: proprio usuario ou admin" on public.profiles;
create policy "Leitura de perfis: proprio usuario ou admin"
on public.profiles
for select
to authenticated
using (
  auth.uid() = id or public.is_admin()
);

-- Atualização: Usuário edita sua própria conta; Admins editam qualquer uma
drop policy if exists "Atualizacao de perfis: proprio usuario ou admin" on public.profiles;
create policy "Atualizacao de perfis: proprio usuario ou admin"
on public.profiles
for update
to authenticated
using (
  auth.uid() = id or public.is_admin()
)
with check (
  auth.uid() = id or public.is_admin()
);

-- 7. Proteção contra escalação de privilégios
create or replace function public.protect_profile_roles()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_admin() then
    -- Bloqueia qualquer alteração de role por não-admin
    if new.role is distinct from old.role then
      raise exception 'Apenas administradores podem alterar o papel (role) de um usuário.';
    end if;

    -- Tratamento do status ativo
    if new.ativo is distinct from old.ativo then
      -- Não pode alterar status de outro usuário
      if auth.uid() <> old.id then
        raise exception 'Você não tem permissão para alterar o status de outro usuário.';
      end if;

      -- Usuário pode desativar a própria conta, mas reativação exige admin
      if old.ativo = false and new.ativo = true then
        raise exception 'Apenas administradores podem reativar uma conta inativa.';
      end if;
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists tr_protect_profile_roles on public.profiles;
create trigger tr_protect_profile_roles
before update on public.profiles
for each row
execute function public.protect_profile_roles();


