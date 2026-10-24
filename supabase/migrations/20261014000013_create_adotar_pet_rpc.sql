-- Function transacional para o processo de adoção de pet
-- Atualiza o status do pet para 'Adotado' e insere o registro correspondente em pets_locais
-- Restringe a operação exclusivamente a pets com status 'Disponível' e a usuários ativos/autenticados

create or replace function public.adotar_pet(
  p_pet_id bigint default null,
  p_pet_local_data jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_pet_id bigint;
  v_local_id bigint;
  v_pet_local_id bigint;
  v_pet record;
begin
  -- 1. Validação de segurança: apenas usuários autenticados e ativos
  if not public.is_active_user() then
    raise exception 'Acesso negado: usuário inativo ou não autenticado.';
  end if;

  -- 2. Identificação do ID do pet (via parâmetro direto ou dentro do jsonb)
  v_pet_id := coalesce(p_pet_id, (p_pet_local_data->>'id_pet')::bigint);
  if v_pet_id is null then
    raise exception 'Identificador do pet (id_pet) não informado.';
  end if;

  -- 3. Identificação do ID do local de destino/adoção
  v_local_id := (p_pet_local_data->>'id_local')::bigint;
  if v_local_id is null then
    raise exception 'Identificador do local (id_local) não informado para registrar o destino da adoção.';
  end if;

  -- 4. Validação de existência do local
  if not exists (select 1 from public.locais where id = v_local_id) then
    raise exception 'Local com ID % não encontrado no cadastro de locais.', v_local_id;
  end if;

  -- 5. Consulta e bloqueio pessimista (FOR UPDATE) do pet
  select id, nome, status
  into v_pet
  from public.pets
  where id = v_pet_id
  for update;

  if not found then
    raise exception 'Pet com ID % não encontrado.', v_pet_id;
  end if;

  -- 6. Validação do status: somente pets atualmente 'Disponível' podem ser adotados
  if lower(trim(v_pet.status)) not in ('disponível', 'disponivel') then
    raise exception 'Não é possível realizar a adoção: o pet "%" (ID %) não está disponível para adoção. Status atual: "%".',
      v_pet.nome, v_pet.id, v_pet.status;
  end if;

  -- 7. Atualiza o status do pet para 'Adotado'
  update public.pets
  set status = 'Adotado'
  where id = v_pet_id;

  -- 8. Insere o histórico de adoção em pets_locais
  insert into public.pets_locais (
    id_local,
    id_pet,
    motivo_saida,
    data_saida,
    data_reentrada,
    valor_auxilio,
    obs,
    updated_by
  )
  values (
    v_local_id,
    v_pet_id,
    coalesce((p_pet_local_data->>'motivo_saida')::varchar(50), 'Adoção'),
    coalesce((p_pet_local_data->>'data_saida')::date, current_date),
    case 
      when p_pet_local_data ? 'data_reentrada' and p_pet_local_data->>'data_reentrada' is not null 
      then (p_pet_local_data->>'data_reentrada')::date 
      else null 
    end,
    case 
      when p_pet_local_data ? 'valor_auxilio' and p_pet_local_data->>'valor_auxilio' is not null 
      then (p_pet_local_data->>'valor_auxilio')::decimal(10,2) 
      else null 
    end,
    (p_pet_local_data->>'obs')::varchar(200),
    auth.uid()
  )
  returning id into v_pet_local_id;

  -- 9. Retorno com os dados da operação
  return jsonb_build_object(
    'success', true,
    'message', format('Adoção do pet "%s" realizada com sucesso!', v_pet.nome),
    'pet_id', v_pet_id,
    'pet_nome', v_pet.nome,
    'pet_status', 'Adotado',
    'id_local', v_local_id,
    'pet_local_id', v_pet_local_id
  );
end;
$$;

comment on function public.adotar_pet(bigint, jsonb) is 'Processa de forma atômica a adoção de um pet: valida status Disponível, atualiza para Adotado e insere registro em pets_locais.';

grant execute on function public.adotar_pet(bigint, jsonb) to authenticated;
