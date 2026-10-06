# Módulo ETL - Peludinhos Caninos

Módulo automatizado de **Extração, Transformação e Carga (ETL)** desenvolvido para migrar a planilha Excel legada de animais resgatados para o banco de dados Supabase (PostgreSQL), em total conformidade com as regras de negócio e interfaces do Frontend.

---

## 📁 Estrutura de Entrada e Saída (`etl/data/`)

O projeto está organizado no padrão de pastas **input** e **output**:

```text
etl/
├── data/
│   ├── input/                     # 📥 Entrada: Coloque aqui o arquivo Excel (.xlsx ou .xls)
│   │   └── .gitkeep               # (Ignorado no Git para proteger dados sensíveis)
│   └── output/                    # 📤 Saída: Arquivos gerados pelo pipeline
│       ├── .gitkeep
│       ├── seed_peludinhos_etl.sql
│       └── peludinhos_clean_data.json
├── models.py                      # Modelos de dados e enums sincronizados com o Frontend
├── extractor.py                   # Leitor XML multi-abas de planilhas .xlsx
├── transformer.py                 # Regras de negócio, inferências e cálculo de senioridade
├── pipeline.py                    # Orquestrador de relacionamentos entre entidades
├── sql_generator.py               # Gerador de instruções SQL transacionais e idempotentes
├── loader.py                      # Carregador automático via container Docker do Supabase
├── main.py                        # CLI principal do pipeline
└── README.md                      # Documentação de uso
```

---

## 🎯 Conformidade com o Frontend e Banco de Dados

O pipeline garante a integridade de todas as colunas `NOT NULL` e respeita os enums/opções do Frontend:

1. **`tipo_pet`**: `'Cachorro'` (padrão de acordo com `TIPO_PET_OPTIONS`).
2. **`sexo`**: `'Macho'` ou `'Fêmea'` (`SEXO_OPTIONS`).
3. **`status`**: `'Disponível'`, `'Adotado'`, `'Óbito'`, `'Em Tratamento'` ou `'Quarentena'` (`STATUS_OPTIONS`).
4. **`senioridade`**: `'Filhote'`, `'Adulto'` ou `'Sênior'` (`SENIORIDADE_OPTIONS`), calculado rigorosamente pela mesma regra do frontend (`calculateSenioridade`):
   - Menos de 12 meses: `'Filhote'`
   - De 1 a menos de 7 anos: `'Adulto'`
   - 7 anos ou mais: `'Sênior'`
5. **`porte`**: `'Médio'` (com identificação de `'Pequeno'`, `'Mini'` ou `'Grande'`).
6. **`raca`**: Identificação automática de raças (`Shih-tzu`, `Poodle`, `Pitbull`, `Dachshund`, `Pinscher`, etc.) com fallback seguro para `'SRD'`.
7. **`data_nascimento` / `data_castracao`**: Conversão de seriais Excel e datas em texto para o formato ISO `YYYY-MM-DD`.
8. **Identificadores (`moura`, `chip`, `rga`)**: Tratamento e remoção de notação científica do Excel.
9. **`vacinas`**: Padronizadas conforme `VACINAS_SUGESTOES` (`'V10 (Déctupla Canina)'`, `'Antirrábica (Raiva)'`, `'Gripe Canina (Tosse dos Canis)'`).
10. **`locais`**: Mapeados conforme `TIPO_LOCAL_OPTIONS` (`'Lar Temporário'`, `'Clínica Veterinária'`, `'Exposição'`, `'Abrigo'`).
11. **`consultas_exames`**: Registro automático dos procedimentos cirúrgicos de castração com `TIPO_OPERACAO_OPTIONS` (`'Procedimento Cirúrgico'`).

---

## 🚀 Como Executar o ETL

O pipeline localiza automaticamente a planilha presente em `etl/data/input/` e salva os resultados em `etl/data/output/`.

### 1. Executar e Carregar Automaticamente no Banco de Dados
Gera a seed em `etl/data/output/seed_peludinhos_etl.sql` e insere todos os dados diretamente no banco do Supabase via Docker:
```powershell
python -m etl.main --load-db
```

### 2. Simulação e Validação Prévia (Dry Run)
Executa a extração e transformação, exibindo o relatório no console sem alterar o banco de dados:
```powershell
python -m etl.main --dry-run
```

### 3. Gerar Apenas o Arquivo SQL de Seed
Gera o arquivo `etl/data/output/seed_peludinhos_etl.sql`:
```powershell
python -m etl.main --generate-sql
```

### 4. Exportar os Dados Higienizados em JSON
Gera o arquivo `etl/data/output/peludinhos_clean_data.json` formatado para uso no Frontend:
```powershell
python -m etl.main --export-json
```

---

## 🔑 Estrutura de Seeds do Supabase

Para garantir total isolamento e evitar conflitos de autenticação:

- **`supabase/seed.sql`**: Contém **apenas** a criação do usuário administrador (`admin@admin.com` / `admin123`) e configuração inicial do `auth.users`, `auth.identities` e `public.profiles`. Executado nativamente pelo comando `supabase db reset`.
- **`etl/data/output/seed_peludinhos_etl.sql`**: Contém **exclusivamente** os dados da carga legada dos pets (288 pets, 288 entradas, 42 locais, 272 estadias, 503 vacinas e 247 procedimentos cirúrgicos). Aplicado via `python -m etl.main --load-db` ou pelo SQL Editor do Studio.
