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

# Mapeamento de equivalências (aliases) para a chave canônica
CANONICAL_LOCAIS_ALIASES: Dict[str, str] = {
    "fucus": "fuçus lindus",
    "fuçus lindus": "fuçus lindus",
    "fuus lindus": "fuçus lindus",
    "casa joyce": "joyce",
    "joice": "joyce",
    "joyce": "joyce",
    "casa joana": "joana",
    "joana": "joana",
    "fatima": "fatima ferreira",
    "fatima ferreira": "fatima ferreira",
    "casa carol": "carol",
}

# Dados enriquecidos dos principais parceiros e lares conhecidos
CANONICAL_LOCAIS_DATA: Dict[str, Dict[str, Any]] = {
    "sitio da port": {
        "local": "Sítio da Port",
        "tipo_local": "Abrigo",
        "contato": "Port (Responsável)",
        "cidade": "Portão",
        "estado": "RS",
        "cep": "93180000",
        "bairro": "Zona Rural",
        "rua": "Estrada da Port",
        "numero": 0,
    },
    "cempra": {
        "local": "CEMPRA - Proteção Animal",
        "tipo_local": "Clínica Veterinária",
        "contato": "Equipe Veterinária CEMPRA",
        "cidade": "Sapiranga",
        "estado": "RS",
        "cep": "93800000",
        "bairro": "Centro",
        "rua": "Avenida 20 de Setembro",
        "numero": 0,
    },
    "bicho livre": {
        "local": "Clínica Veterinária Bicho Livre",
        "tipo_local": "Clínica Veterinária",
        "contato": "Equipe Bicho Livre",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "tierplatz": {
        "local": "Associação Tierplatz",
        "tipo_local": "Abrigo",
        "contato": "Equipe Tierplatz",
        "cidade": "Taquara",
        "estado": "RS",
        "cep": "95600000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "petz": {
        "local": "Espaço Petz de Adoção",
        "tipo_local": "Exposição",
        "contato": "Gerência Petz",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Centro",
        "rua": "Não Informada",
        "numero": 0,
    },
    "sao paulo": {
        "local": "Acolhimento São Paulo",
        "tipo_local": "Lar Temporário",
        "contato": "Parceiro Acolhedor SP",
        "cidade": "São Paulo",
        "estado": "SP",
        "cep": "01001000",
        "bairro": "Centro",
        "rua": "Não Informada",
        "numero": 0,
    },
    "bruno tutor": {
        "local": "Tutor Bruno",
        "tipo_local": "Lar Temporário",
        "contato": "Bruno (Tutor)",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "joyce": {
        "local": "Lar Temporário Joyce",
        "tipo_local": "Lar Temporário",
        "contato": "Joyce",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Santo Afonso",
        "rua": "Não Informada",
        "numero": 0,
    },
    "aline pet papa": {
        "local": "Lar Temporário Aline (Pet Papa)",
        "tipo_local": "Lar Temporário",
        "contato": "Aline",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "fuçus lindus": {
        "local": "Lar Temporário Fuçus Lindus",
        "tipo_local": "Lar Temporário",
        "contato": "Responsável Fuçus Lindus",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "fatima ferreira": {
        "local": "Lar Temporário Fátima Ferreira",
        "tipo_local": "Lar Temporário",
        "contato": "Fátima Ferreira",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "joana": {
        "local": "Lar Temporário Joana",
        "tipo_local": "Lar Temporário",
        "contato": "Joana",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "carol": {
        "local": "Lar Temporário Carol",
        "tipo_local": "Lar Temporário",
        "contato": "Carol",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "habitat": {
        "local": "Lar Temporário Habitat",
        "tipo_local": "Lar Temporário",
        "contato": "Responsável Habitat",
        "cidade": "Sapiranga",
        "estado": "RS",
        "cep": "93800000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "fernanda": {
        "local": "Lar Temporário Fernanda",
        "tipo_local": "Lar Temporário",
        "contato": "Fernanda",
        "cidade": "Sapiranga",
        "estado": "RS",
        "cep": "93800000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "solange": {
        "local": "Lar Temporário Solange",
        "tipo_local": "Lar Temporário",
        "contato": "Solange",
        "cidade": "Sapiranga",
        "estado": "RS",
        "cep": "93800000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "lara": {
        "local": "Lar Temporário Lara",
        "tipo_local": "Lar Temporário",
        "contato": "Lara",
        "cidade": "Sapiranga",
        "estado": "RS",
        "cep": "93800000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "kamille": {
        "local": "Lar Temporário Kamille",
        "tipo_local": "Lar Temporário",
        "contato": "Kamille",
        "cidade": "Sapiranga",
        "estado": "RS",
        "cep": "93800000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "santa": {
        "local": "Lar Temporário Santa",
        "tipo_local": "Lar Temporário",
        "contato": "Santa",
        "cidade": "Sapiranga",
        "estado": "RS",
        "cep": "93800000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
    "amiga sil": {
        "local": "Lar Temporário Amiga Sil",
        "tipo_local": "Lar Temporário",
        "contato": "Silvia / Amiga Sil",
        "cidade": "Novo Hamburgo",
        "estado": "RS",
        "cep": "93300000",
        "bairro": "Não Informado",
        "rua": "Não Informada",
        "numero": 0,
    },
}

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
    def resolve_local(raw_name: Optional[str]) -> Tuple[Optional[str], Optional[LocalRecord]]:
        """
        Normaliza, deduplica e enriquece semanticamente a estadia da planilha legada,
        retornando uma tupla (nome_canonico, LocalRecord) ou (None, None) se for anomalia/inválido.
        """
        if not raw_name:
            return None, None
        
        cleaned = str(raw_name).strip()
        if not cleaned or cleaned in ("?", "-", "N/A", "n/a", "--"):
            return None, None
        
        key = cleaned.lower()
        canonical_key = CANONICAL_LOCAIS_ALIASES.get(key, key)
        
        if canonical_key in CANONICAL_LOCAIS_DATA:
            data = CANONICAL_LOCAIS_DATA[canonical_key]
            record = LocalRecord(
                local=data["local"],
                tipo_local=data["tipo_local"],
                contato=data["contato"],
                telefone="00000000000",
                cidade=data["cidade"],
                estado=data["estado"],
                cep=data["cep"],
                bairro=data["bairro"],
                rua=data["rua"],
                numero=data["numero"]
            )
            return record.local, record
        
        # Para lares pessoais de voluntários
        if not cleaned.lower().startswith("lar temporário"):
            display_local = f"Lar Temporário {cleaned}"
        else:
            display_local = cleaned
            
        record = LocalRecord(
            local=display_local[:50],
            tipo_local="Lar Temporário",
            contato=cleaned[:50],
            telefone="00000000000",
            cidade="Novo Hamburgo",
            estado="RS",
            cep="93300000",
            bairro="Não Informado",
            rua="Não Informada",
            numero=0
        )
        return record.local, record

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
