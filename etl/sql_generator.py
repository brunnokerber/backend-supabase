"""
Módulo Gerador de SQL: Gera instruções SQL transacionais e seguras
para inserção de todos os dados extraídos e transformados no Supabase/PostgreSQL.
"""
from typing import Dict, List, Any
from etl.models import (
    PetRecord, EntradaRecord, LocalRecord, PetLocalRecord, VacinaRecord,
    VeterinarioRecord, ConsultaExameRecord
)

def sql_escape(val: Any) -> str:
    """Escapa e formata valores para literais seguros em comandos SQL."""
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    s = str(val).replace("'", "''")
    return f"'{s}'"

class SQLGenerator:
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def generate_sql(self, output_path: str) -> str:
        """Gera o script SQL de carga com suporte a idempotência e integridade referencial."""
        sql_lines = [
            "-- ====================================================================",
            "-- Dados de Carga (Seed) ETL: Peludinhos Caninos",
            "-- Gerado automaticamente pelo Pipeline ETL respeitando o Frontend e o Banco",
            "-- ====================================================================",
            "",
            "SET client_encoding = 'UTF8';",
            "",
            "-- Configuração de variáveis e bloco transacional PL/pgSQL",
            "DO $$",

            "DECLARE",
            "  v_admin_id uuid;",
            "  v_pet_id bigint;",
            "  v_local_id bigint;",
            "  v_vet_id bigint;",
            "BEGIN",
            "",
            "  -- 1. Obter ID de usuário administrador ativo existente no banco",
            "  SELECT id INTO v_admin_id FROM auth.users ORDER BY created_at ASC LIMIT 1;",
            "  IF v_admin_id IS NULL THEN",
            "    v_admin_id := 'a0000000-0000-0000-0000-000000000001'::uuid;",
            "  END IF;",
            "",
            "  -- 2. Inserção dos Locais (Lares Temporários, Clínicas, Exposições)",
        ]

        # 2. Locais
        locais: List[LocalRecord] = self.data.get("locais", [])
        for loc in locais:
            sql_lines.append(f"""  IF NOT EXISTS (SELECT 1 FROM public.locais WHERE local = {sql_escape(loc.local)}) THEN
    INSERT INTO public.locais (tipo_local, contato, telefone, local, bairro, rua, numero, complemento, cidade, estado, cep)
    VALUES ({sql_escape(loc.tipo_local)}, {sql_escape(loc.contato)}, {sql_escape(loc.telefone)}, {sql_escape(loc.local)}, {sql_escape(loc.bairro)}, {sql_escape(loc.rua)}, {loc.numero}, {sql_escape(loc.complemento)}, {sql_escape(loc.cidade)}, {sql_escape(loc.estado)}, {sql_escape(loc.cep)});
  END IF;""")

        # 3. Pets e suas relações (entradas, pets_locais, vacinas, consultas_exames)
        sql_lines.append("\n  -- 3. Inserção dos Pets, Entradas, Histórico de Locais, Vacinas e Consultas/Exames")

        
        pets: List[PetRecord] = self.data.get("pets", [])
        entradas_map = {e.pet_ref: e for e in self.data.get("entradas", [])}
        pets_locais_map = {}
        for pl in self.data.get("pets_locais", []):
            pets_locais_map.setdefault(pl.pet_ref, []).append(pl)
        vacinas_map = {}
        for v in self.data.get("vacinas", []):
            vacinas_map.setdefault(v.pet_ref, []).append(v)
        consultas_map = {}
        for c in self.data.get("consultas_exames", []):
            consultas_map.setdefault(c.pet_ref, []).append(c)

        for p in pets:
            sql_lines.append(f"""
  -- Pet: {p.nome}
  SELECT id INTO v_pet_id FROM public.pets WHERE nome = {sql_escape(p.nome)} LIMIT 1;
  IF v_pet_id IS NULL THEN
    INSERT INTO public.pets (
      tipo_pet, sexo, status, nome, senioridade, data_nascimento, data_castracao,
      link_documentos, foto_url, cor_majoritaria, raca, porte, moura, chip, rga
    )
    VALUES (
      {sql_escape(p.tipo_pet)}, {sql_escape(p.sexo)}, {sql_escape(p.status)}, {sql_escape(p.nome)},
      {sql_escape(p.senioridade)}, {sql_escape(p.data_nascimento)}, {sql_escape(p.data_castracao)},
      {sql_escape(p.link_documentos)}, {sql_escape(p.foto_url)}, {sql_escape(p.cor_majoritaria)}, {sql_escape(p.raca)},
      {sql_escape(p.porte)}, {sql_escape(p.moura)}, {sql_escape(p.chip)}, {sql_escape(p.rga)}
    )
    RETURNING id INTO v_pet_id;
  END IF;""")

            # Entrada
            if p.nome in entradas_map:
                ent = entradas_map[p.nome]
                sql_lines.append(f"""  IF NOT EXISTS (SELECT 1 FROM public.entradas WHERE id_pet = v_pet_id) THEN
    INSERT INTO public.entradas (id_usuario, id_pet, local_origem, data_entrada, resgatante, observacoes)
    VALUES (v_admin_id, v_pet_id, {sql_escape(ent.local_origem)}, {sql_escape(ent.data_entrada)}::date, {sql_escape(ent.resgatante)}, {sql_escape(ent.observacoes)});
  END IF;""")

            # Histórico de Hospedagem (Pets Locais)
            if p.nome in pets_locais_map:
                for pl in pets_locais_map[p.nome]:
                    val_aux_sql = str(pl.valor_auxilio) if pl.valor_auxilio is not None else "NULL"
                    sql_lines.append(f"""  SELECT id INTO v_local_id FROM public.locais WHERE local = {sql_escape(pl.local_nome)} LIMIT 1;
  IF v_local_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.pets_locais WHERE id_pet = v_pet_id AND id_local = v_local_id) THEN
    INSERT INTO public.pets_locais (id_local, id_pet, motivo_saida, data_reentrada, data_saida, valor_auxilio, obs)
    VALUES (v_local_id, v_pet_id, {sql_escape(pl.motivo_saida)}, {sql_escape(pl.data_reentrada)}, {sql_escape(pl.data_saida)}::date, {val_aux_sql}, {sql_escape(pl.obs)});
  END IF;""")

            # Vacinas
            if p.nome in vacinas_map:
                for vac in vacinas_map[p.nome]:
                    dt_prev = sql_escape(vac.data_prevista)
                    dt_aplic = sql_escape(vac.data_aplicacao)
                    custo_sql = str(vac.custo) if vac.custo is not None else "NULL"
                    sql_lines.append(f"""  INSERT INTO public.vacinas (id_pet, id_veterinario, nome_vacina, data_prevista, data_aplicacao, custo)
    VALUES (v_pet_id, NULL, {sql_escape(vac.nome_vacina)}, {dt_prev}::date, {dt_aplic}::date, {custo_sql});""")

            # Consultas e Procedimentos Clínicos / Cirúrgicos (Castração)
            if p.nome in consultas_map:
                for ce in consultas_map[p.nome]:
                    dt_real = sql_escape(ce.data_realizacao)
                    custo_sql = str(ce.custo) if ce.custo is not None else "NULL"
                    sql_lines.append(f"""  IF NOT EXISTS (SELECT 1 FROM public.consultas_exames WHERE id_pet = v_pet_id AND tipo_operacao = {sql_escape(ce.tipo_operacao)} AND data_realizacao = {dt_real}::date) THEN
    INSERT INTO public.consultas_exames (id_pet, id_veterinario, operacao_medicamento, data_realizacao, custo, tipo_operacao)
    VALUES (v_pet_id, NULL, {sql_escape(ce.operacao_medicamento)}, {dt_real}::date, {custo_sql}, {sql_escape(ce.tipo_operacao)});
  END IF;""")

        sql_lines.extend([
            "",
            "END $$;",
            "-- ====================================================================",
            "-- Fim do Script de Seed ETL",
            "-- ===================================================================="
        ])

        full_sql = "\n".join(sql_lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_sql)

        return full_sql
