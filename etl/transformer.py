"""
Módulo de transformação: higieniza, enriquece, infere e normaliza os dados dos pets,
respeitando rigorosamente as restrições do banco de dados e as regras do frontend.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any, Set
from etl.models import (
    PetRecord, EntradaRecord, LocalRecord, PetLocalRecord, VacinaRecord, VeterinarioRecord,
    ConsultaExameRecord, TIPO_PET_OPTIONS, SEXO_OPTIONS, STATUS_OPTIONS, SENIORIDADE_OPTIONS,
    PORTE_OPTIONS, TIPO_OPERACAO_OPTIONS, VACINAS_SUGESTOES, TIPO_LOCAL_OPTIONS,
    DEFAULT_ADMIN_USER_ID
)

# Palavras-chave conhecidas para identificação de sexo
PALAVRAS_CHAVE_FEMEA = [
    'femea', 'fêmea', 'femeas', 'menina', 'castrada', 'prenha', 'adotada', 'devolvida',
    'mae', 'mãe', 'filhota', 'gata', 'cadela'
]
PALAVRAS_CHAVE_MACHO = [
    'macho', 'machos', 'menino', 'castrado', 'adotado', 'devolvido', 'pai', 'filhote', 'gato', 'cao', 'cão'
]

# Mapeamento de raças comuns identificadas no texto
RACAS_COMUNS = [
    ('shitzu', 'Shih-tzu'),
    ('shih tzu', 'Shih-tzu'),
    ('shih-tzu', 'Shih-tzu'),
    ('poodle', 'Poodle'),
    ('pitt', 'Pitbull'),
    ('pitbull', 'Pitbull'),
    ('pit bull', 'Pitbull'),
    ('pinscher', 'Pinscher'),
    ('dachshund', 'Dachshund'),
    ('teckel', 'Dachshund'),
    ('yorkshire', 'Yorkshire'),
    ('pastor', 'Pastor Alemão'),
    ('labrador', 'Labrador'),
    ('golden', 'Golden Retriever'),
    ('chow chow', 'Chow-chow'),
    ('rotweiller', 'Rottweiler'),
    ('rottweiler', 'Rottweiler'),
    ('border collie', 'Border Collie'),
    ('beagle', 'Beagle'),
    ('schnauzer', 'Schnauzer'),
    ('pug', 'Pug'),
    ('husky', 'Husky Siberiano'),
    ('boxer', 'Boxer'),
    ('dalmata', 'Dálmata'),
    ('basset', 'Basset'),
    ('cocker', 'Cocker Spaniel'),
    ('maltes', 'Maltês'),
    ('vira-lata', 'SRD'),
    ('srd', 'SRD')
]

class PetTransformer:
    @staticmethod
    def parse_date(value: Optional[str]) -> Optional[str]:
        """
        Converte números seriais do Excel, anos (ex: 2022) ou datas em texto (DD/MM/YYYY) para o formato ISO YYYY-MM-DD.
        """
        if not value:
            return None
        val_str = str(value).strip()
        if not val_str:
            return None

        # 1. Verificar número serial float do Excel
        try:
            val_f = float(val_str)
            # Apenas ano (ex: 2018.0)
            if 1990 <= val_f <= 2050 and int(val_f) == val_f:
                return f"{int(val_f):04d}-01-01"
            # Dias seriais do Excel
            if 30000 <= val_f <= 65000:
                base = datetime(1899, 12, 30)
                dt = base + timedelta(days=val_f)
                return dt.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass

        # 2. Formatos textuais como DD/MM/YYYY ou DD/MM/YY
        m = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', val_str)
        if m:
            d, month, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if y < 100:
                y += 2000
            try:
                dt = datetime(y, month, d)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        return None

    @staticmethod
    def calculate_senioridade(birth_iso: Optional[str]) -> str:
        """
        Calcula a senioridade/fase de vida exatamente pela regra do Frontend (calculateSenioridade):
        - Menos de 12 meses: Filhote
        - De 1 a menos de 7 anos: Adulto
        - 7 anos ou mais: Sênior
        """
        if not birth_iso:
            return "Adulto"

        try:
            parts = [int(p) for p in birth_iso.split("-")]
            birth = datetime(parts[0], parts[1], parts[2])
            today = datetime.now()
            
            years = today.year - birth.year
            months = today.month - birth.month

            if today.day < birth.day:
                months -= 1
            if months < 0:
                years -= 1
                months += 12

            total_months = years * 12 + months

            if total_months < 12:
                return "Filhote"
            if years < 7:
                return "Adulto"
            return "Sênior"
        except Exception:
            return "Adulto"

    @staticmethod
    def infer_sexo(nome: str, context_text: str = "") -> str:
        """
        Infere 'Macho' ou 'Fêmea' com base em palavras-chave, qualificadores e desinências de nomes.
        """
        combined = f"{nome} {context_text}".lower()

        # Palavras-chave diretas e explícitas
        for kw in PALAVRAS_CHAVE_FEMEA:
            if re.search(rf'\b{kw}\b', combined):
                return "Fêmea"
        for kw in PALAVRAS_CHAVE_MACHO:
            if re.search(rf'\b{kw}\b', combined):
                return "Macho"

        # Verificar o primeiro nome limpo
        clean_first = nome.strip().split()[0].rstrip("().,")
        clean_first_lower = clean_first.lower()

        excecoes_machos = {'apolo', 'luca', 'puma', 'sasha', 'buda', 'dunga', 'juca', 'simba', 'zeca', 'cacau', 'kaka', 'boris'}
        excecoes_femeas = {'mel', 'sol', 'jade', 'meg', 'meggie', 'lily', 'lili', 'daisy', 'suzi', 'suzy', 'isis', 'bel'}

        if clean_first_lower in excecoes_machos:
            return "Macho"
        if clean_first_lower in excecoes_femeas:
            return "Fêmea"

        # Terminações em 'a', 'inha' ou 'ete' em português são predominantemente femininas
        if clean_first_lower.endswith("a") or clean_first_lower.endswith("inha") or clean_first_lower.endswith("ete"):
            return "Fêmea"

        return "Macho"

    @staticmethod
    def normalize_status(raw_status: Optional[str], sheet_name: str, notes: str = "") -> str:
        """
        Normaliza para um dos valores do enum do Frontend: 'Disponível', 'Em Tratamento', 'Quarentena', 'Adotado', 'Óbito'.
        """
        raw = (raw_status or "").strip().lower()
        sheet = sheet_name.strip().upper()

        if "OBITO" in sheet or "obito" in raw or "óbito" in raw or "virou estrelinha" in raw or "faleceu" in raw or "morreu" in raw:
            return "Óbito"

        if "ADOTADO" in sheet or "adotad" in raw or "doado" in raw:
            return "Adotado"

        if "tratamento" in raw:
            return "Em Tratamento"

        if "quarentena" in raw:
            return "Quarentena"

        # Se foi devolvido, o pet volta a estar disponível
        if "devolvid" in raw or "devolução" in raw or "devolucao" in raw:
            return "Disponível"

        return "Disponível"

    @staticmethod
    def normalize_nome_vacina(raw_name: str) -> str:
        """
        Mapeia a descrição da vacina para as opções sugeridas no Frontend (VACINAS_SUGESTOES).
        """
        lower = raw_name.lower().strip()
        if "dhppi" in lower or "dhpp" in lower or "poli" in lower:
            return "DHPPI (Polivalente Canina)"
        if "v10" in lower or "decupla" in lower or "déctupla" in lower:
            return "V10 (Déctupla Canina)"
        if "v8" in lower or "octupla" in lower or "óctupla" in lower:
            return "V8 (Óctupla Canina)"
        if "raiva" in lower or "antirrabica" in lower or "antirrábica" in lower:
            return "Antirrábica (Raiva)"
        if "gripe" in lower or "tosse" in lower or "mara" in lower:
            return "Gripe Canina (Tosse dos Canis)"
        if "giardia" in lower or "giardiase" in lower or "giárdiase" in lower:
            return "Giárdiase"
        if "leish" in lower:
            return "Leishmaniose"
        if "v3" in lower or "triplice" in lower or "tríplice" in lower:
            return "Tríplice Felina (V3)"
        if "v4" in lower or "quadrupla" in lower or "quádrupla" in lower:
            return "Quádrupla Felina (V4)"
        if "v5" in lower or "quintupla" in lower or "quíntupla" in lower:
            return "Quíntupla Felina (V5)"
        
        return "DHPPI (Polivalente Canina)"

    @staticmethod
    def normalize_tipo_local(nome_local: str) -> str:
        """
        Mapeia o local para as opções válidas no Frontend (TIPO_LOCAL_OPTIONS):
        'Lar Temporário', 'Clínica Veterinária', 'Exposição', 'Abrigo', 'CCZ', 'Outro'.
        """
        lower = nome_local.lower()
        if any(w in lower for w in ['vet', 'clinica', 'clínica', 'hospital', 'espaço animal', 'cempra']):
            return "Clínica Veterinária"
        if any(w in lower for w in ['petz', 'feira', 'evento', 'exposi', 'shopping']):
            return "Exposição"
        if any(w in lower for w in ['abrigo', 'canil', 'tierplatz']):
            return "Abrigo"
        if "ccz" in lower or "zoonose" in lower:
            return "CCZ"
        
        return "Lar Temporário"

    @staticmethod
    def infer_raca(text: str) -> str:
        """
        Identifica a raça a partir do texto ou retorna 'SRD' (Sem Raça Definida) como fallback seguro.
        """
        lower = text.lower()
        for pattern, raca_name in RACAS_COMUNS:
            if re.search(rf'\b{pattern}\b', lower):
                return raca_name
        return "SRD"

    @staticmethod
    def clean_identifier(val: Optional[str]) -> Optional[str]:
        """
        Remove notação científica e pontos flutuantes de moura, chip e rga.
        """
        if not val:
            return None
        s = str(val).strip()
        if not s or s.lower() in ('none', 'null', '-', '--'):
            return None

        # Tratar notação científica (ex: 9.63E14)
        try:
            if 'e' in s.lower():
                val_f = float(s)
                return str(int(val_f))
            if s.endswith(".0"):
                return str(int(float(s)))
        except (ValueError, OverflowError):
            pass

        return s

    @staticmethod
    def parse_currency(val: Optional[str]) -> Optional[float]:
        """
        Converte valores monetários textuais (ex: 'R$150,00', '150.0', '295') para float.
        """
        if not val:
            return None
        s = str(val).strip().replace("R$", "").replace("r$", "").replace(" ", "")
        try:
            # Formato brasileiro com vírgula decimal
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            return float(s)
        except ValueError:
            return None
