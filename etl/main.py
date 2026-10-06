"""
Ponto de entrada principal para o Pipeline de ETL do Peludinhos Caninos.
Organização estruturada em etl/data/input (planilhas) e etl/data/output (SQL/JSON).
"""
import argparse
import glob
import json
import os
import sys

# Configurar saída padrão para UTF-8 em consoles Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from etl.pipeline import PeludinhosETLPipeline
from etl.sql_generator import SQLGenerator
from etl.loader import DatabaseLoader

DEFAULT_INPUT_DIR = "etl/data/input"
DEFAULT_OUTPUT_DIR = "etl/data/output"
DEFAULT_SQL_OUTPUT = os.path.join(DEFAULT_OUTPUT_DIR, "seed_peludinhos_etl.sql")
DEFAULT_JSON_OUTPUT = os.path.join(DEFAULT_OUTPUT_DIR, "peludinhos_clean_data.json")

def find_default_excel_file(input_dir: str) -> str:
    """Procura automaticamente o primeiro arquivo Excel (.xlsx ou .xls) na pasta de entrada."""
    files = glob.glob(os.path.join(input_dir, "*.xlsx")) + glob.glob(os.path.join(input_dir, "*.xls"))
    if files:
        return files[0]
    return os.path.join(input_dir, "peludinhos_lista_geral.xlsx")

def print_summary(data: dict):
    """Exibe no console o relatório formatado com métricas da extração e transformação."""
    pets = data["pets"]
    entradas = data["entradas"]
    locais = data["locais"]
    pets_locais = data["pets_locais"]
    vacinas = data["vacinas"]
    consultas = data.get("consultas_exames", [])

    print("\n" + "=" * 65)
    print("           RELATÓRIO DE EXTRAÇÃO E TRANSFORMAÇÃO (ETL)           ")
    print("=" * 65)
    print(f"🐶 Total de Pets Processados:             {len(pets)}")
    print(f"📥 Registros de Entradas:                 {len(entradas)}")
    print(f"🏠 Locais / Lares Temporários:            {len(locais)}")
    print(f"📍 Histórico de Hospedagem (Pets_Locais): {len(pets_locais)}")
    print(f"💉 Doses de Vacinas Mapeadas:             {len(vacinas)}")
    print(f"🩺 Consultas e Procedimentos Cirúrgicos:  {len(consultas)}")
    print("-" * 65)

    # Distribuição de status
    status_counts = {}
    for p in pets:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1
    print("📊 Distribuição de Status dos Pets:")
    for st, count in sorted(status_counts.items()):
        print(f"   • {st:<18}: {count:>3} pets")

    # Distribuição por senioridade
    sen_counts = {}
    for p in pets:
        sen_counts[p.senioridade] = sen_counts.get(p.senioridade, 0) + 1
    print("\n⏳ Distribuição por Senioridade (Regra do Frontend):")
    for sn, count in sorted(sen_counts.items()):
        print(f"   • {sn:<18}: {count:>3} pets")

    # Distribuição por sexo
    sex_counts = {}
    for p in pets:
        sex_counts[p.sexo] = sex_counts.get(p.sexo, 0) + 1
    print("\n⚧ Distribuição por Sexo:")
    for sx, count in sorted(sex_counts.items()):
        print(f"   • {sx:<18}: {count:>3} pets")

    # Distribuição de tipos de vacinas mapeadas
    vac_counts = {}
    for v in vacinas:
        vac_counts[v.nome_vacina] = vac_counts.get(v.nome_vacina, 0) + 1
    print("\n💉 Distribuição de Vacinas Padronizadas (Enums Frontend):")
    for v_nome, count in sorted(vac_counts.items()):
        print(f"   • {v_nome:<32}: {count:>3} doses")

    # Distribuição de tipos de locais
    loc_counts = {}
    for l in locais:
        loc_counts[l.tipo_local] = loc_counts.get(l.tipo_local, 0) + 1
    print("\n🏠 Distribuição de Tipos de Locais (Enums Frontend):")
    for l_tipo, count in sorted(loc_counts.items()):
        print(f"   • {l_tipo:<25}: {count:>3} locais")

    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="ETL Peludinhos Caninos -> Supabase/PostgreSQL")
    parser.add_argument("--file", "-f", default=None, help=f"Caminho da planilha Excel (padrão: busca em {DEFAULT_INPUT_DIR})")
    parser.add_argument("--dry-run", action="store_true", help="Executa o pipeline e exibe validação sem alterar o banco")
    parser.add_argument("--generate-sql", action="store_true", help="Gera arquivo SQL de seed para o Supabase")
    parser.add_argument("--sql-output", default=DEFAULT_SQL_OUTPUT, help=f"Caminho do arquivo SQL gerado (padrão: {DEFAULT_SQL_OUTPUT})")
    parser.add_argument("--export-json", action="store_true", help="Exporta dados transformados em formato JSON")
    parser.add_argument("--json-output", default=DEFAULT_JSON_OUTPUT, help=f"Caminho do arquivo JSON (padrão: {DEFAULT_JSON_OUTPUT})")
    parser.add_argument("--load-db", action="store_true", help="Aplica o SQL gerado diretamente no banco de dados do Supabase (via Docker)")

    args = parser.parse_args()

    # Resolver arquivo Excel de entrada
    excel_file = args.file or find_default_excel_file(DEFAULT_INPUT_DIR)

    if not os.path.exists(excel_file):
        print(f"❌ Erro: Planilha não encontrada em: {excel_file}")
        print(f"💡 Dica: Coloque sua planilha .xlsx dentro da pasta '{DEFAULT_INPUT_DIR}/'")
        sys.exit(1)

    # Garantir que pasta de saída exista
    os.makedirs(os.path.dirname(args.sql_output) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.json_output) or ".", exist_ok=True)

    print(f"🚀 Iniciando Pipeline ETL a partir de: {excel_file}")
    pipeline = PeludinhosETLPipeline(excel_file)
    data = pipeline.run()

    print_summary(data)

    # Sempre gera o SQL se solicitado ou se for carregar no banco ou por padrão
    if args.generate_sql or args.load_db or not (args.dry_run or args.export_json):
        print(f"\n📝 Gerando script SQL transacional em: {args.sql_output} ...")
        generator = SQLGenerator(data)
        generator.generate_sql(args.sql_output)
        print(f"✅ Script SQL gerado com sucesso! ({args.sql_output})")

    if args.export_json:
        print(f"\n💾 Exportando JSON estruturado em: {args.json_output} ...")
        
        def serialize(obj):
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(data, f, default=serialize, ensure_ascii=False, indent=2)
        print(f"✅ Arquivo JSON exportado com sucesso! ({args.json_output})")

    if args.load_db:
        print(f"\n⚡ Carregando dados no banco Supabase...")
        loader = DatabaseLoader(args.sql_output)
        loader.load_via_docker()

    print("\n✨ Processo de ETL concluído com sucesso!")

if __name__ == "__main__":
    main()
