"""
Pipeline de ETL: Orquestra a Extração, Transformação e Vinculação de Entidades.
"""
from typing import Dict, List, Any, Optional, Set, Tuple
from etl.extractor import ExcelExtractor
from etl.transformer import PetTransformer
from etl.models import (
    PetRecord, EntradaRecord, LocalRecord, PetLocalRecord, VacinaRecord, VeterinarioRecord,
    ConsultaExameRecord, DEFAULT_ADMIN_USER_ID, STATUS_OPTIONS, PORTE_OPTIONS,
    SENIORIDADE_OPTIONS, SEXO_OPTIONS, TIPO_OPERACAO_OPTIONS, VACINAS_SUGESTOES, TIPO_LOCAL_OPTIONS
)
import re

class PeludinhosETLPipeline:
    def __init__(self, excel_path: str, admin_user_id: str = DEFAULT_ADMIN_USER_ID):
        self.excel_path = excel_path
        self.admin_user_id = admin_user_id
        self.extractor = ExcelExtractor(excel_path)
        self.transformer = PetTransformer()

        # Coleções de saída
        self.pets: List[PetRecord] = []
        self.entradas: List[EntradaRecord] = []
        self.locais: Dict[str, LocalRecord] = {} # Mapeado pelo nome do local
        self.pets_locais: List[PetLocalRecord] = []
        self.vacinas: List[VacinaRecord] = []
        self.consultas_exames: List[ConsultaExameRecord] = []
        
        # Controle para evitar duplicatas de pets entre abas
        self.seen_pet_names: Set[str] = set()

    def run(self) -> Dict[str, Any]:
        """
        Executa todo o processo de extração, transformação e relacionamentos.
        """
        self._process_pet_sheet("LISTA GERAL")
        self._process_pet_sheet("ADOTADOS")
        self._process_pet_sheet("OBITOSDEVOL")
        self._process_vacinas_filhotes()
        self._process_vacinas_adultos()

        return {
            "pets": self.pets,
            "entradas": self.entradas,
            "locais": list(self.locais.values()),
            "pets_locais": self.pets_locais,
            "vacinas": self.vacinas,
            "consultas_exames": self.consultas_exames
        }


    def _process_pet_sheet(self, sheet_name: str):
        """Processa as abas principais de cadastro de pets (Lista Geral, Adotados, Óbitos/Devoluções)."""
        rows = self.extractor.read_sheet(sheet_name)
        if not rows:
            return

        header_row = rows[0][1]
        data_rows = rows[1:]

        for r_num, row in data_rows:
            raw_nome = row.get('B')
            if not raw_nome:
                continue

            # Nome novo (se houver preferência ou junção com apelido)
            nome_novo = row.get('C')
            clean_name = raw_nome.strip()
            
            # Formatação do nome para exibição
            display_name = clean_name
            if nome_novo and nome_novo.strip() and nome_novo.strip().lower() != clean_name.lower():
                display_name = f"{clean_name} ({nome_novo.strip()})"

            # Limite de tamanho (varchar(30) no schema do banco)
            final_name = display_name[:30].strip()

            # Evitar duplicatas se o mesmo pet aparecer em múltiplas abas
            pet_key = final_name.lower()
            if pet_key in self.seen_pet_names:
                continue
            self.seen_pet_names.add(pet_key)

            # Extração dos campos brutos da linha conforme novo layout
            raw_status = row.get('A')
            raw_sexo = row.get('D')
            raw_nasc = row.get('E')
            raw_estadia = row.get('F')
            raw_obs_estadia = row.get('G')
            raw_pre_resgate = row.get('H')
            raw_resgatante = row.get('I')
            raw_entrada = row.get('J')
            raw_castracao = row.get('K')
            raw_local_vet = row.get('L')
            raw_historico = row.get('M')
            raw_exposicao = row.get('N')
            raw_observacoes = row.get('O')
            raw_poli = row.get('P')
            raw_reforco1 = row.get('Q')
            raw_reforco2 = row.get('R')
            raw_raiva = row.get('S')

            # Tratamento de colunas pós-coluna S dependendo da aba
            if sheet_name == 'LISTA GERAL':
                raw_reforco_raiva = None
                raw_docs = row.get('T_link') or (row.get('T') if str(row.get('T', '')).strip().startswith(('http://', 'https://')) else None)
                raw_moura = row.get('U')
                raw_chip = row.get('V')
                raw_rga = row.get('W')
                raw_adotante = None
                raw_telefone = None
                raw_email = None
                raw_tag = None
            elif sheet_name == 'ADOTADOS':
                raw_reforco_raiva = row.get('T')
                raw_docs = row.get('U_link') or (row.get('U') if str(row.get('U', '')).strip().startswith(('http://', 'https://')) else None)
                raw_moura = row.get('V')
                raw_chip = row.get('W')
                raw_rga = row.get('X')
                raw_adotante = row.get('Y')
                raw_telefone = row.get('Z')
                raw_email = row.get('AA')
                raw_tag = row.get('AB')
            else: # OBITOSDEVOL
                raw_reforco_raiva = row.get('T')
                raw_docs = row.get('U_link') or (row.get('U') if str(row.get('U', '')).strip().startswith(('http://', 'https://')) else None)
                raw_moura = row.get('V')
                raw_chip = row.get('W')
                raw_rga = None
                raw_adotante = row.get('X')
                raw_telefone = row.get('Y')
                raw_email = None
                raw_tag = None

            # Contexto textual para enriquecimento e inferências
            combined_context = f"{clean_name} {raw_observacoes or ''} {raw_historico or ''} {raw_pre_resgate or ''}"

            # 1. Transformação dos dados do Pet
            data_nasc_iso = self.transformer.parse_date(raw_nasc)
            data_castracao_iso = self.transformer.parse_date(raw_castracao)
            
            # Se a coluna de castração contém "castrado(a)" ou "sim", mas sem data explícita
            if not data_castracao_iso and raw_castracao and any(w in raw_castracao.lower() for w in ['castrad', 'sim', 'ok']):
                data_castracao_iso = data_nasc_iso or "2023-01-01"

            # Sexo: normalizar se presente na coluna D, senão inferir
            if raw_sexo and str(raw_sexo).strip().lower() in ('femea', 'fêmea'):
                sexo = "Fêmea"
            elif raw_sexo and str(raw_sexo).strip().lower() in ('macho',):
                sexo = "Macho"
            else:
                sexo = self.transformer.infer_sexo(clean_name, combined_context)

            status = self.transformer.normalize_status(raw_status, sheet_name, combined_context)
            senioridade = self.transformer.calculate_senioridade(data_nasc_iso)
            raca = self.transformer.infer_raca(combined_context)
            porte = "Médio" # Padrão seguro
            if "pequeno" in combined_context.lower() or "mini" in combined_context.lower():
                porte = "Pequeno"
            elif "grande" in combined_context.lower():
                porte = "Grande"

            chip_cleaned = self.transformer.clean_identifier(raw_chip)
            moura_cleaned = self.transformer.clean_identifier(raw_moura)
            rga_cleaned = self.transformer.clean_identifier(raw_rga)

            obs_pet_parts = []
            if raw_observacoes:
                obs_pet_parts.append(f"Obs: {raw_observacoes}")
            if raw_historico:
                obs_pet_parts.append(f"Hist: {raw_historico}")
            if raw_exposicao and raw_exposicao.strip() not in ('-', 'N/A', ''):
                obs_pet_parts.append(f"Exp: {raw_exposicao}")

            pet = PetRecord(
                nome=final_name,
                tipo_pet="Cachorro",
                sexo=sexo,
                status=status,
                senioridade=senioridade,
                raca=raca,
                porte=porte,
                data_nascimento=data_nasc_iso,
                data_castracao=data_castracao_iso,
                link_documentos=raw_docs.strip() if raw_docs else None,
                cor_majoritaria=None,
                moura=moura_cleaned[:30] if moura_cleaned else None,
                chip=chip_cleaned[:30] if chip_cleaned else None,
                rga=rga_cleaned[:30] if rga_cleaned else None,
                original_sheet=sheet_name,
                original_row=r_num,
                observacoes_gerais=" | ".join(obs_pet_parts) if obs_pet_parts else None
            )
            self.pets.append(pet)

            # 2. Transformação do Registro de Entrada
            data_entrada_iso = self.transformer.parse_date(raw_entrada) or data_nasc_iso or "2023-01-01"
            
            # Resgatante: coluna explícita 'I' com fallback seguro
            resgatante_str = (raw_resgatante or "Peludinhos Caninos").strip()[:50]
            if not resgatante_str:
                resgatante_str = "Peludinhos Caninos"

            # Local de Origem: coluna 'H' (Pré resgate), histórico ou padrão
            origem_str = (raw_pre_resgate or raw_historico or "Resgate / Acolhimento").strip()[:50]
            if not origem_str:
                origem_str = "Resgate / Acolhimento"
            
            obs_entrada_parts = []
            if raw_observacoes:
                obs_entrada_parts.append(f"Obs: {raw_observacoes}")
            if raw_historico and raw_historico != raw_pre_resgate:
                obs_entrada_parts.append(f"Hist: {raw_historico}")
            if raw_exposicao and raw_exposicao.strip() not in ('-', 'N/A', ''):
                obs_entrada_parts.append(f"Exp: {raw_exposicao}")
            if raw_adotante:
                obs_entrada_parts.append(f"Adotante: {raw_adotante} (Tel: {raw_telefone or 'N/A'}, Email: {raw_email or 'N/A'})")
            if raw_tag:
                obs_entrada_parts.append(f"Tag: {raw_tag}")

            entrada = EntradaRecord(
                pet_ref=final_name,
                id_usuario=self.admin_user_id,
                local_origem=origem_str,
                data_entrada=data_entrada_iso,
                resgatante=resgatante_str,
                observacoes=" | ".join(obs_entrada_parts) if obs_entrada_parts else None
            )
            self.entradas.append(entrada)

            # 3. Transformação de Locais e Pets_Locais (Hospedagem)
            if raw_estadia and raw_estadia.strip():
                nome_can, loc_rec = self.transformer.resolve_local(raw_estadia)
                if loc_rec is not None:
                    if nome_can not in self.locais:
                        self.locais[nome_can] = loc_rec
                    
                    valor_aux = self.transformer.parse_currency(raw_obs_estadia)
                    pet_local = PetLocalRecord(
                        pet_ref=final_name,
                        local_nome=nome_can,
                        data_saida=data_entrada_iso,
                        valor_auxilio=valor_aux,
                        obs=raw_observacoes[:200] if raw_observacoes else None
                    )
                    self.pets_locais.append(pet_local)

            # 4. Consultas/Exames e Vacinas

            # Procedimento Cirúrgico de Castração (ConsultaExame)
            if data_castracao_iso:
                self.consultas_exames.append(ConsultaExameRecord(
                    pet_ref=final_name,
                    tipo_operacao="Procedimento Cirúrgico",
                    operacao_medicamento="Procedimento de Castração e Esterilização",
                    data_realizacao=data_castracao_iso,
                    veterinario_ref=None
                ))

            # Vacinas registradas nas colunas da linha
            vacina_cols = [
                ("DHPPI (Polivalente Canina)", raw_poli),
                ("DHPPI (Polivalente Canina)", raw_reforco1),
                ("DHPPI (Polivalente Canina)", raw_reforco2),
                ("Antirrábica (Raiva)", raw_raiva)
            ]
            if raw_reforco_raiva:
                vacina_cols.append(("Antirrábica (Raiva)", raw_reforco_raiva))

            for vac_nome, raw_vac_val in vacina_cols:
                if raw_vac_val:
                    data_vac_iso = self.transformer.parse_date(raw_vac_val)
                    if data_vac_iso:
                        self.vacinas.append(VacinaRecord(
                            pet_ref=final_name,
                            nome_vacina=vac_nome,
                            data_prevista=data_vac_iso,
                            data_aplicacao=data_vac_iso,
                            veterinario_ref=raw_local_vet.strip()[:50] if raw_local_vet else None
                        ))

    def _process_vacinas_filhotes(self):
        """Processa a aba de vacinação de filhotes."""
        try:
            rows = self.extractor.read_sheet("Vacinas filhotes")
        except Exception:
            return
        if len(rows) < 4:
            return

        # Leitura a partir da linha 4 de dados
        for r_num, row in rows[3:]:
            nome_pet = row.get('B')
            if not nome_pet:
                continue
            clean_name = nome_pet.strip()[:30]

            v_cols = [
                ("DHPPI (Polivalente Canina)", row.get('C')),
                ("DHPPI (Polivalente Canina)", row.get('D')),
                ("DHPPI (Polivalente Canina)", row.get('E')),
                ("DHPPI (Polivalente Canina)", row.get('F')),
                ("Antirrábica (Raiva)", row.get('G'))
            ]
            for v_name, val in v_cols:
                dt_iso = self.transformer.parse_date(val)
                if dt_iso:
                    self.vacinas.append(VacinaRecord(
                        pet_ref=clean_name,
                        nome_vacina=v_name,
                        data_prevista=dt_iso,
                        data_aplicacao=dt_iso
                    ))

    def _process_vacinas_adultos(self):
        """Processa a matriz anual da aba de vacinas de adultos."""
        try:
            rows = self.extractor.read_sheet("Vacinas Adultos")
        except Exception:
            return
        if len(rows) < 4:
            return

        for r_num, row in rows[3:]:
            nome_pet = row.get('B')
            if not nome_pet:
                continue
            clean_name = nome_pet.strip()[:30]

            # Iterar pelas colunas de anos/vacinas
            poli_cols = {'C', 'E', 'F', 'G', 'J', 'K', 'L', 'N', 'O', 'P'}
            raiva_cols = {'D', 'H', 'M', 'Q'}
            for col_letter, val in row.items():
                if col_letter in ('A', 'B') or not val:
                    continue
                dt_iso = self.transformer.parse_date(val)
                if dt_iso:
                    if col_letter in poli_cols:
                        v_name = "DHPPI (Polivalente Canina)"
                    elif col_letter in raiva_cols:
                        v_name = "Antirrábica (Raiva)"
                    elif col_letter == 'I':
                        v_name = "Gripe Canina (Tosse dos Canis)"
                    else:
                        v_name = "DHPPI (Polivalente Canina)"
                    self.vacinas.append(VacinaRecord(
                        pet_ref=clean_name,
                        nome_vacina=v_name,
                        data_prevista=dt_iso,
                        data_aplicacao=dt_iso
                    ))
