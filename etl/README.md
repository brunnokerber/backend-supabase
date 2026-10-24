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
2. **`sexo`**: `'Macho'` ou `'Fêmea'` (`SEXO_OPTIONS`). Mapeado diretamente da coluna **`D` (Sexo)**, com fallback para inferência por desinência de nome e palavras-chave caso não preenchido.
3. **`status`**: `'Disponível'`, `'Adotado'`, `'Óbito'`, `'Em Tratamento'` ou `'Quarentena'` (`STATUS_OPTIONS`), inferido pela coluna **`A` (Situação)** e pelo nome da aba.
4. **`senioridade`**: `'Filhote'`, `'Adulto'` ou `'Sênior'` (`SENIORIDADE_OPTIONS`), calculado rigorosamente pela data de nascimento da coluna **`E` (Idade/nasc)** seguindo a mesma regra do frontend (`calculateSenioridade`):
   - Menos de 12 meses: `'Filhote'`
   - De 1 a menos de 7 anos: `'Adulto'`
   - 7 anos ou mais: `'Sênior'`
5. **`porte`**: `'Médio'` (com identificação de `'Pequeno'`, `'Mini'` ou `'Grande'`).
6. **`raca`**: Identificação automática de raças (`Shih-tzu`, `Poodle`, `Pitbull`, `Dachshund`, `Pinscher`, etc.) com fallback seguro para `'SRD'`.
7. **`data_nascimento` / `data_castracao`**: Conversão de seriais Excel e datas em texto das colunas **`E`** e **`K`** para o formato ISO `YYYY-MM-DD`.
8. **Entrada e Acolhimento (`entradas`)**:
   - **`resgatante`**: Mapeado diretamente da coluna **`I` (Resgatante)**, com fallback para `'Peludinhos Caninos'`.
   - **`local_origem`**: Mapeado a partir da coluna **`H` (Pré resgate)** e histórico de resgate.
   - **`data_entrada`**: Extraído da coluna **`J` (Entrada/Resgate)** com fallback para a data de nascimento.
9. **Identificadores (`moura`, `chip`, `rga`, `link_documentos`)**:
   - `link_documentos`: Extração da URL real do hiperlink associado à célula na coluna **`T`** (`LISTA GERAL`) ou **`U`** (`ADOTADOS` / `OBITOSDEVOL`), preservando links externos de armazenamento (ex: Google Drive).
   - `moura`: Coluna **`U`** (`LISTA GERAL`) ou **`V`** (`ADOTADOS` / `OBITOSDEVOL`).
   - `chip`: Coluna **`V`** (`LISTA GERAL`) ou **`W`** (`ADOTADOS` / `OBITOSDEVOL`).
   - `rga`: Coluna **`W`** (`LISTA GERAL`) ou **`X`** (`ADOTADOS`).
   - Remoção de notação científica flutuante do Excel (ex: `9.63E14` -> microchip de 15 dígitos).
10. **`vacinas`**: Padronizadas conforme `VACINAS_SUGESTOES` (`'DHPPI (Polivalente Canina)'`, `'Antirrábica (Raiva)'`, `'Gripe Canina (Tosse dos Canis)'`, `'V10 (Déctupla Canina)'`, etc.). Cobre doses iniciais e reforços das colunas **`P`**, **`Q`**, **`R`**, **`S`** e **`T`** (reforço de raiva), além das matrizes anuais das abas de filhotes e adultos.
11. **`locais` e Hospedagem (`pets_locais`)**: Mapeados a partir da coluna **`F` (Estadia)** e valor de auxílio na coluna **`G` (Obs)** com normalização canônica e enriquecimento semântico:
    - **Deduplicação de Grafias:** Unificação de variações da planilha (`Fuçus Lindus` / `Fucus`, `Casa Joyce` / `Joice` / `Joyce`, `Casa Joana` / `Joana`, `Fatima` / `Fatima Ferreira`, `Casa Carol` / `Carol`).
    - **Remoção de Ruído:** Estadias com valor `?` ou traço são ignoradas (evitando cadastros lixo no banco).
    - **Enriquecimento dos Principais Parceiros:** Mapeamento preciso de tipos e contatos para parceiros conhecidos:
      - `Sítio da Port`: Tipo `'Abrigo'`, Cidade: `'Portão - RS'`, Bairro: `'Zona Rural'`, Contato: `'Port (Responsável)'`.
      - `CEMPRA - Proteção Animal`: Tipo `'Clínica Veterinária'`, Cidade: `'Sapiranga - RS'`, Bairro: `'Centro'`, Contato: `'Equipe Veterinária CEMPRA'`.
      - `Clínica Veterinária Bicho Livre`: Tipo `'Clínica Veterinária'`, Cidade: `'Novo Hamburgo - RS'`.
      - `Espaço Petz de Adoção`: Tipo `'Exposição'`, Cidade: `'Novo Hamburgo - RS'`, Bairro: `'Centro'`.
      - `Associação Tierplatz`: Tipo `'Abrigo'`, Cidade: `'Taquara - RS'`.
      - `Acolhimento São Paulo`: Tipo `'Lar Temporário'`, Cidade: `'São Paulo - SP'`.
      - `Lar Temporário Joyce`: Bairro: `'Santo Afonso'`.
      - Lares de Sapiranga com cidade correta (`Fernanda`, `Habitat`, `Kamille`, `Lara`, `Santa`, `Solange`).
    - **Contatos Semânticos e Endereço Explícito:** O campo `contato` recebe o nome da pessoa responsável (não mais a cópia do nome do local). Endereços desconhecidos usam claramente `rua: "Não Informada"`, `numero: 0`, `bairro: "Não Informado"` para evidenciar pendência cadastral.
12. **`consultas_exames`**: Registro automático dos procedimentos cirúrgicos de castração a partir da coluna **`K` (Castração)** com `TIPO_OPERACAO_OPTIONS` (`'Procedimento Cirúrgico'`).

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

- **`supabase/seed.sql`**: Contém **apenas** a criação do usuário administrador (`admin@admin.com` / `Admin@123`) e configuração inicial do `auth.users`, `auth.identities` e `public.profiles`. Executado nativamente pelo comando `supabase db reset`.
- **`etl/data/output/seed_peludinhos_etl.sql`**: Contém **exclusivamente** os dados da carga legada dos pets (347 pets, 347 entradas, 38 locais consolidados, 329 estadias/pets_locais, 538 doses de vacinas e 289 procedimentos cirúrgicos). Aplicado via `python -m etl.main --load-db` ou pelo SQL Editor do Studio.
