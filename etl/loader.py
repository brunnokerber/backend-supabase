"""
Módulo Carregador (Loader): Aplica os dados do ETL diretamente no banco de dados Supabase/PostgreSQL.
Suporta execução via Docker (sem necessidade de instalar o cliente psql no Windows).
"""
import subprocess
import os
import sys

class DatabaseLoader:
    def __init__(self, sql_file_path: str):
        self.sql_file_path = sql_file_path

    def find_supabase_db_container(self) -> str:
        """Localiza o nome do container Docker do banco de dados do Supabase."""
        try:
            res = subprocess.run(
                ["docker", "ps", "--filter", "name=supabase_db", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True
            )
            containers = [c.strip() for c in res.stdout.splitlines() if c.strip()]
            if containers:
                return containers[0]
        except Exception:
            pass
        return "supabase_db_backend-supabase"

    def load_via_docker(self) -> bool:
        """Executa o arquivo SQL diretamente no container PostgreSQL do Supabase."""
        if not os.path.exists(self.sql_file_path):
            print(f"❌ Arquivo SQL não encontrado: {self.sql_file_path}")
            return False

        container_name = self.find_supabase_db_container()
        print(f"📦 Conectando ao container Docker: {container_name} ...")

        try:
            with open(self.sql_file_path, "rb") as sql_file:
                cmd = [
                    "docker", "exec", "-i",
                    "-e", "PGCLIENTENCODING=UTF8",
                    container_name,
                    "psql", "-U", "postgres", "-d", "postgres"
                ]
                proc = subprocess.run(cmd, stdin=sql_file, capture_output=True, text=True, encoding="utf-8")

                if proc.returncode == 0:
                    print(f"✅ Dados aplicados com sucesso no banco de dados!")
                    return True
                else:
                    print(f"❌ Erro ao aplicar SQL no banco: {proc.stderr}")
                    return False

        except FileNotFoundError:
            print("❌ Docker não encontrado no PATH do sistema. Certifique-se de que o Docker Desktop está aberto.")
            return False
        except Exception as e:
            print(f"❌ Falha inesperada durante a carga: {e}")
            return False
