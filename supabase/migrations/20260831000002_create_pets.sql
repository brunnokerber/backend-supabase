create table if not exists public.pets (
  id bigint generated always as identity primary key,
  tipo_pet varchar(30) not null,
  sexo varchar(30) not null,
  status varchar(30) not null,
  nome varchar(30) not null,
  senioridade varchar(30) not null,
  data_nascimento date,
  data_castracao date,
  link_documentos text,
  foto_url text,
  cor_majoritaria varchar(30),
  raca varchar(30) not null,
  porte varchar(30) not null,  
  moura varchar(30),
  chip varchar(30),
  rga varchar(30),
  updated_by uuid references public.profiles(id) on delete set null default auth.uid(),
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
  using (public.is_active_user());

drop policy if exists "Users can insert pets" on public.pets;
create policy "Users can insert pets"
  on public.pets
  for insert
  to authenticated
  with check (public.is_active_user());

drop policy if exists "Users can update pets" on public.pets;
create policy "Users can update pets"
  on public.pets
  for update
  to authenticated
  using (public.is_active_user());

drop trigger if exists set_pets_updated_at on public.pets;
create trigger set_pets_updated_at
before update on public.pets
for each row execute function public.handle_updated_at();

-- Criação do Bucket 'pets' no Supabase Storage
-- Privado (public = false): visualização restrita a usuários autenticados
-- file_size_limit: 262144 bytes (256 KB)
-- allowed_mime_types: apenas imagens jpeg, png e webp
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'pets',
  'pets',
  false,
  262144,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Políticas de Segurança (Row Level Security) em storage.objects para o bucket 'pets'

-- Leitura: apenas usuários autenticados e ativos
drop policy if exists "Authenticated active users can read pet images" on storage.objects;
create policy "Authenticated active users can read pet images"
  on storage.objects
  for select
  to authenticated
  using (bucket_id = 'pets' and public.is_active_user());

-- Upload (inserção): apenas usuários autenticados e ativos
drop policy if exists "Authenticated active users can upload pet images" on storage.objects;
create policy "Authenticated active users can upload pet images"
  on storage.objects
  for insert
  to authenticated
  with check (bucket_id = 'pets' and public.is_active_user());

-- Atualização / substituição de imagem: apenas usuários autenticados e ativos
drop policy if exists "Authenticated active users can update pet images" on storage.objects;
create policy "Authenticated active users can update pet images"
  on storage.objects
  for update
  to authenticated
  using (bucket_id = 'pets' and public.is_active_user());

-- Exclusão: restrita a administradores
drop policy if exists "Admins can delete pet images" on storage.objects;
create policy "Admins can delete pet images"
  on storage.objects
  for delete
  to authenticated
  using (bucket_id = 'pets' and public.is_admin());