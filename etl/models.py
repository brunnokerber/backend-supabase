"""
Modelos de dados e constantes alinhados com as interfaces TypeScript do Frontend e esquema do banco.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Constantes correspondentes às opções e enums do Frontend
TIPO_PET_OPTIONS = ['Cachorro', 'Gato', 'Outro']
SEXO_OPTIONS = ['Macho', 'Fêmea']
STATUS_OPTIONS = ['Disponível', 'Em Tratamento', 'Quarentena', 'Adotado', 'Óbito']
SENIORIDADE_OPTIONS = ['Filhote', 'Adulto', 'Sênior']
PORTE_OPTIONS = ['Mini', 'Pequeno', 'Médio', 'Grande', 'Gigante']

TIPO_OPERACAO_OPTIONS = [
    'Consulta de Rotina',
    'Consulta Emergencial',
    'Exame de Sangue',
    'Exame de Imagem',
    'Procedimento Cirúrgico',
    'Medicamento',
    'Outro',
]

VACINAS_SUGESTOES = [
    'V8 (Óctupla Canina)',
    'V10 (Déctupla Canina)',
    'Antirrábica (Raiva)',
    'Giárdiase',
    'Gripe Canina (Tosse dos Canis)',
    'Leishmaniose',
    'Tríplice Felina (V3)',
    'Quádrupla Felina (V4)',
    'Quíntupla Felina (V5)',
]

TIPO_LOCAL_OPTIONS = [
    'Lar Temporário',
    'Clínica Veterinária',
    'Exposição',
    'Abrigo',
    'CCZ',
    'Outro',
]

DEFAULT_ADMIN_USER_ID = "a0000000-0000-0000-0000-000000000001"

@dataclass
class PetRecord:
    """Registro representativo da tabela public.pets."""
    nome: str
    tipo_pet: str = "Cachorro"
    sexo: str = "Macho"
    status: str = "Disponível"
    senioridade: str = "Adulto"
    raca: str = "SRD"
    porte: str = "Médio"
    data_nascimento: Optional[str] = None
    data_castracao: Optional[str] = None
    link_documentos: Optional[str] = None
    cor_majoritaria: Optional[str] = None
    moura: Optional[str] = None
    chip: Optional[str] = None
    rga: Optional[str] = None
    
    # Metadados de rastreabilidade para o ETL
    temp_id: Optional[str] = None
    original_sheet: Optional[str] = None
    original_row: Optional[int] = None
    observacoes_gerais: Optional[str] = None

@dataclass
class EntradaRecord:
    """Registro de acolhimento/resgate para a tabela public.entradas."""
    pet_ref: str
    id_usuario: str
    local_origem: str
    data_entrada: str
    resgatante: str
    observacoes: Optional[str] = None

@dataclass
class LocalRecord:
    """Registro de lar temporário, clínica ou abrigo na tabela public.locais."""
    local: str
    tipo_local: str = "Lar Temporário"
    contato: str = "Responsável Local"
    telefone: str = "00000000000"
    bairro: str = "Centro"
    rua: str = "Principal"
    numero: int = 1
    complemento: Optional[str] = None
    cidade: str = "Novo Hamburgo"
    estado: str = "RS"
    cep: str = "93300000"

@dataclass
class PetLocalRecord:
    """Histórico de estadia/hospedagem na tabela public.pets_locais."""
    pet_ref: str
    local_nome: str
    data_saida: str # Data de início da hospedagem ou registro
    data_reentrada: Optional[str] = None
    motivo_saida: Optional[str] = None
    valor_auxilio: Optional[float] = None
    obs: Optional[str] = None

@dataclass
class VacinaRecord:
    """Registro de dose de vacina na tabela public.vacinas."""
    pet_ref: str
    nome_vacina: str
    data_prevista: str
    data_aplicacao: Optional[str] = None
    custo: Optional[float] = None
    veterinario_ref: Optional[str] = None

@dataclass
class ConsultaExameRecord:
    """Registro de procedimento clínico na tabela public.consultas_exames."""
    pet_ref: str
    tipo_operacao: str
    operacao_medicamento: str
    data_realizacao: str
    custo: Optional[float] = None
    veterinario_ref: Optional[str] = None

@dataclass
class VeterinarioRecord:
    """Registro de médico veterinário na tabela public.veterinarios."""
    nome: str
    telefone: str = "00000000000"
    crvet: str = "00000"

