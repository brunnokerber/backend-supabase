create table if not exists entradas(
  id bigint generated always as identity primary key,
  id_usuario uuid not null references auth.users(id) on delete cascade,
  id_pet bigint not null references public.pets(id) on delete cascade,
  local_origem varchar(50) not null,
  data_entrada date not null,
  resgatante varchar(50) not null,
  observacoes text,
  updated_by uuid references public.profiles(id) on delete set null default auth.uid(),
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
  using (public.is_active_user());

drop policy if exists "Authenticated users can insert entradas" on public.entradas;
create policy "Authenticated users can insert entradas"
  on public.entradas
  for insert
  to authenticated
  with check (public.is_active_user());

drop policy if exists "Authenticated users can update entradas" on public.entradas;
create policy "Authenticated users can update entradas"
  on public.entradas
  for update
  to authenticated
  using (public.is_active_user());

drop trigger if exists set_entradas_updated_at on public.entradas;
create trigger set_entradas_updated_at
before update on public.entradas
for each row
execute function public.handle_updated_at();

-- Function transacional para atualização atômica de pet e seus dados de entrada
create or replace function public.update_pet_com_entrada(
  p_pet_id bigint,
  p_pet_data jsonb,
  p_entrada_data jsonb default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
begin
  -- Validação de segurança: apenas usuários ativos e autenticados
  if not public.is_active_user() then
    raise exception 'Acesso negado: usuário inativo ou não autenticado.';
  end if;

  -- 1. Atualiza a tabela pets
  update public.pets
  set 
    nome             = coalesce((p_pet_data->>'nome')::varchar(30), nome),
    tipo_pet         = coalesce((p_pet_data->>'tipo_pet')::varchar(30), tipo_pet),
    sexo             = coalesce((p_pet_data->>'sexo')::varchar(30), sexo),
    status           = coalesce((p_pet_data->>'status')::varchar(30), status),
    senioridade      = coalesce((p_pet_data->>'senioridade')::varchar(30), senioridade),
    raca             = coalesce((p_pet_data->>'raca')::varchar(30), raca),
    porte            = coalesce((p_pet_data->>'porte')::varchar(30), porte),
    cor_majoritaria  = coalesce((p_pet_data->>'cor_majoritaria')::varchar(30), cor_majoritaria),
    data_nascimento  = case when p_pet_data ? 'data_nascimento' then (p_pet_data->>'data_nascimento')::date else data_nascimento end,
    data_castracao   = case when p_pet_data ? 'data_castracao' then (p_pet_data->>'data_castracao')::date else data_castracao end,
    link_documentos  = case when p_pet_data ? 'link_documentos' then (p_pet_data->>'link_documentos')::text else link_documentos end,
    foto_url         = case when p_pet_data ? 'foto_url' then (p_pet_data->>'foto_url')::text else foto_url end,
    moura            = case when p_pet_data ? 'moura' then (p_pet_data->>'moura')::varchar(30) else moura end,
    chip             = case when p_pet_data ? 'chip' then (p_pet_data->>'chip')::varchar(30) else chip end,
    rga              = case when p_pet_data ? 'rga' then (p_pet_data->>'rga')::varchar(30) else rga end
  where id = p_pet_id;

  if not found then
    raise exception 'Pet com ID % não encontrado.', p_pet_id;
  end if;

  -- 2. Atualiza a tabela entradas vinculada ao pet (se fornecido)
  if p_entrada_data is not null then
    update public.entradas
    set 
      local_origem = coalesce((p_entrada_data->>'local_origem')::varchar(50), local_origem),
      data_entrada = coalesce((p_entrada_data->>'data_entrada')::date, data_entrada),
      resgatante   = coalesce((p_entrada_data->>'resgatante')::varchar(50), resgatante),
      observacoes  = case when p_entrada_data ? 'observacoes' then (p_entrada_data->>'observacoes')::text else observacoes end
    where id_pet = p_pet_id;
  end if;

  return jsonb_build_object('success', true, 'pet_id', p_pet_id);
end;
$$;

grant execute on function public.update_pet_com_entrada(bigint, jsonb, jsonb) to authenticated;

-- Function transacional para criação atômica de pet e seus dados de entrada
create or replace function public.create_pet_com_entrada(
  p_pet_data jsonb,
  p_entrada_data jsonb default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_pet_id bigint;
  v_entrada_id bigint;
  v_user_id uuid;
begin
  -- Validação de segurança: apenas usuários ativos e autenticados
  if not public.is_active_user() then
    raise exception 'Acesso negado: usuário inativo ou não autenticado.';
  end if;

  -- Determina o usuário responsável (da sessão auth.uid() ou informado no payload)
  v_user_id := coalesce((p_entrada_data->>'id_usuario')::uuid, auth.uid());

  -- 1. Insere o pet na tabela pets
  insert into public.pets (
    nome,
    tipo_pet,
    sexo,
    status,
    senioridade,
    raca,
    porte,
    cor_majoritaria,
    data_nascimento,
    data_castracao,
    link_documentos,
    foto_url,
    moura,
    chip,
    rga,
    updated_by
  )
  values (
    (p_pet_data->>'nome')::varchar(30),
    coalesce((p_pet_data->>'tipo_pet')::varchar(30), 'Cachorro'),
    (p_pet_data->>'sexo')::varchar(30),
    coalesce((p_pet_data->>'status')::varchar(30), 'Disponível'),
    coalesce((p_pet_data->>'senioridade')::varchar(30), 'Adulto'),
    coalesce((p_pet_data->>'raca')::varchar(30), 'SRD'),
    coalesce((p_pet_data->>'porte')::varchar(30), 'Médio'),
    (p_pet_data->>'cor_majoritaria')::varchar(30),
    (p_pet_data->>'data_nascimento')::date,
    (p_pet_data->>'data_castracao')::date,
    (p_pet_data->>'link_documentos')::text,
    (p_pet_data->>'foto_url')::text,
    (p_pet_data->>'moura')::varchar(30),
    (p_pet_data->>'chip')::varchar(30),
    (p_pet_data->>'rga')::varchar(30),
    v_user_id
  )
  returning id into v_pet_id;

  -- 2. Insere os dados de entrada vinculados ao pet (se fornecidos)
  if p_entrada_data is not null then
    if v_user_id is null then
      raise exception 'Usuário responsável não identificado para o registro de entrada.';
    end if;

    insert into public.entradas (
      id_usuario,
      id_pet,
      local_origem,
      data_entrada,
      resgatante,
      observacoes,
      updated_by
    )
    values (
      v_user_id,
      v_pet_id,
      coalesce((p_entrada_data->>'local_origem')::varchar(50), 'Não informado'),
      coalesce((p_entrada_data->>'data_entrada')::date, current_date),
      coalesce((p_entrada_data->>'resgatante')::varchar(50), 'Não informado'),
      (p_entrada_data->>'observacoes')::text,
      v_user_id
    )
    returning id into v_entrada_id;
  end if;

  return jsonb_build_object(
    'success', true,
    'pet_id', v_pet_id,
    'entrada_id', v_entrada_id
  );
end;
$$;

grant execute on function public.create_pet_com_entrada(jsonb, jsonb) to authenticated;


