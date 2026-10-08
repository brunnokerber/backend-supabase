-- Migration: Criação de índices para otimização de performance e busca textual
-- 1. Habilita extensão de busca por trigramas (pg_trgm) no schema extensions
create extension if not exists pg_trgm with schema extensions;

-- 2. Índices de Chaves Estrangeiras (FKs) - Essenciais para JOINs e integridade relacional
create index if not exists idx_entradas_id_pet on public.entradas(id_pet);
create index if not exists idx_entradas_id_usuario on public.entradas(id_usuario);
create index if not exists idx_vacinas_id_pet on public.vacinas(id_pet);
create index if not exists idx_vacinas_id_veterinario on public.vacinas(id_veterinario);
create index if not exists idx_consultas_exames_id_pet on public.consultas_exames(id_pet);
create index if not exists idx_consultas_exames_id_veterinario on public.consultas_exames(id_veterinario);
create index if not exists idx_pets_locais_id_pet on public.pets_locais(id_pet);
create index if not exists idx_pets_locais_id_local on public.pets_locais(id_local);
create index if not exists idx_direcionamento_doacoes_id_doacao on public.direcionamento_doacoes(id_doacao);
create index if not exists idx_direcionamento_doacoes_id_local on public.direcionamento_doacoes(id_local);

-- 3. Índices Compostos para Ordenação de Prontuário Clínico e Estadias (por Pet)
create index if not exists idx_vacinas_pet_data on public.vacinas(id_pet, data_aplicacao desc nulls last);
create index if not exists idx_consultas_pet_data on public.consultas_exames(id_pet, data_realizacao desc nulls last);
create index if not exists idx_pets_locais_pet_data on public.pets_locais(id_pet, data_saida desc nulls last);

-- 4. Índices para Filtros e Ordenação de Listagem de Pets (/pets)
create index if not exists idx_pets_filtros on public.pets(status, tipo_pet, senioridade, porte);
create index if not exists idx_pets_id_desc on public.pets(id desc);
create index if not exists idx_pets_created_at_desc on public.pets(created_at desc);

-- 5. Índices de Identificadores (Busca exata ou prefixo)
create index if not exists idx_pets_chip on public.pets(chip) where chip is not null;
create index if not exists idx_pets_moura on public.pets(moura) where moura is not null;
create index if not exists idx_pets_rga on public.pets(rga) where rga is not null;
create index if not exists idx_veterinarios_crmv on public.veterinarios(crmv);

-- 6. Busca Textual Otimizada por Trigramas (GIN / ILIKE '%termo%')
create index if not exists idx_pets_nome_trgm on public.pets using gin (nome extensions.gin_trgm_ops);
create index if not exists idx_pets_raca_trgm on public.pets using gin (raca extensions.gin_trgm_ops);
create index if not exists idx_locais_nome_trgm on public.locais using gin (local extensions.gin_trgm_ops);
create index if not exists idx_locais_bairro_trgm on public.locais using gin (bairro extensions.gin_trgm_ops);
create index if not exists idx_locais_cidade_trgm on public.locais using gin (cidade extensions.gin_trgm_ops);
create index if not exists idx_veterinarios_nome_trgm on public.veterinarios using gin (nome extensions.gin_trgm_ops);
create index if not exists idx_profiles_created_at_desc on public.profiles(created_at desc);

-- 7. Índices para Módulo de Voluntários (/voluntarios)
create index if not exists idx_voluntarios_nome_trgm on public.voluntarios using gin (nome extensions.gin_trgm_ops);
create index if not exists idx_voluntarios_dias_semana on public.voluntarios using gin (dias_semana);
create index if not exists idx_voluntarios_turnos on public.voluntarios using gin (turnos);
create index if not exists idx_voluntarios_created_at_desc on public.voluntarios(created_at desc);
