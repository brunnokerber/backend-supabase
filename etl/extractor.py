"""
Módulo extrator para ler e processar arquivos Excel (.xlsx) legados.
Utiliza a biblioteca padrão zipfile e o analisador XML para execução sem dependências externas.
"""
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple
import os

class ExcelExtractor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        self.shared_strings: List[str] = []
        self.sheet_map: Dict[str, str] = {} # Nome da aba -> caminho do XML
        self._load_metadata()

    def _load_metadata(self):
        """Carrega a tabela de strings compartilhadas e o mapeamento de abas da planilha."""
        with zipfile.ZipFile(self.file_path, "r") as z:
            # 1. Carregar strings compartilhadas (sharedStrings.xml)
            if "xl/sharedStrings.xml" in z.namelist():
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                    text = "".join([t.text for t in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text])
                    self.shared_strings.append(text)

            # 2. Mapear nomes das abas para os arquivos XML correspondentes
            # Leitura dos relacionamentos do workbook
            rels = {}
            if "xl/_rels/workbook.xml.rels" in z.namelist():
                rel_tree = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
                for r in rel_tree.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                    r_id = r.attrib.get("Id")
                    target = r.attrib.get("Target")
                    if target.startswith("/"):
                        target = target[1:]
                    elif not target.startswith("xl/"):
                        target = "xl/" + target
                    rels[r_id] = target

            wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
            sheets = wb_tree.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")
            for s in sheets:
                name = s.attrib.get("name")
                r_id = s.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                target = rels.get(r_id, f"xl/worksheets/sheet{s.attrib.get('sheetId')}.xml")
                self.sheet_map[name] = target

    def get_sheet_names(self) -> List[str]:
        """Retorna os nomes de todas as abas encontradas na pasta de trabalho."""
        return list(self.sheet_map.keys())

    def _load_sheet_hyperlinks(self, z: zipfile.ZipFile, xml_path: str) -> Dict[str, str]:
        """Extrai o mapeamento de referência da célula (ex: 'T2') para a URL do hiperlink."""
        sheet_dir, sheet_file = os.path.split(xml_path)
        rels_path = f"{sheet_dir}/_rels/{sheet_file}.rels"
        rels = {}
        if rels_path in z.namelist():
            try:
                rtree = ET.fromstring(z.read(rels_path))
                for r in rtree.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                    r_id = r.attrib.get("Id")
                    target = r.attrib.get("Target")
                    if r_id and target:
                        rels[r_id] = target
            except Exception:
                pass

        hyperlinks = {}
        try:
            stree = ET.fromstring(z.read(xml_path))
            hl_tag = stree.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}hyperlinks")
            if hl_tag is not None:
                for hl in hl_tag.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}hyperlink"):
                    ref = hl.attrib.get("ref")
                    r_id = hl.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                    target = rels.get(r_id) or hl.attrib.get("location")
                    if ref and target:
                        hyperlinks[ref] = target
        except Exception:
            pass

        return hyperlinks

    def get_sheet_hyperlinks(self, sheet_name: str) -> Dict[str, str]:
        """Retorna todos os hiperlinks da aba especificada no formato {ref_celula: url}."""
        xml_path = self.sheet_map.get(sheet_name)
        if not xml_path:
            for k, v in self.sheet_map.items():
                if k.lower() == sheet_name.lower():
                    xml_path = v
                    break
        if not xml_path:
            return {}
        with zipfile.ZipFile(self.file_path, "r") as z:
            return self._load_sheet_hyperlinks(z, xml_path)

    def read_sheet(self, sheet_name: str) -> List[Tuple[int, Dict[str, str]]]:
        """
        Retorna uma lista de tuplas (numero_da_linha, {letra_coluna: valor_celula}) para linhas não vazias.
        Se uma célula possuir hiperlink associado, disponibiliza também a chave '{letra_coluna}_link' com a URL.
        """
        xml_path = self.sheet_map.get(sheet_name)
        if not xml_path:
            # Tentar correspondência insensível a maiúsculas/minúsculas
            for k, v in self.sheet_map.items():
                if k.lower() == sheet_name.lower():
                    xml_path = v
                    break
        if not xml_path:
            raise ValueError(f"Aba '{sheet_name}' não encontrada no arquivo.")

        with zipfile.ZipFile(self.file_path, "r") as z:
            sheet_hyperlinks = self._load_sheet_hyperlinks(z, xml_path)
            s_xml = z.read(xml_path)
            tree = ET.fromstring(s_xml)
            rows_data = []
            for row in tree.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                r_idx = int(row.attrib.get("r", 0))
                cols = {}
                for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                    r = c.attrib.get("r", "")
                    col_letter = "".join([ch for ch in r if ch.isalpha()])
                    t = c.attrib.get("t")
                    v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                    val = v.text if v is not None else None
                    if t == "s" and val is not None:
                        try:
                            val = self.shared_strings[int(val)]
                        except (IndexError, ValueError):
                            pass
                    elif t == "inlineStr":
                        is_node = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is")
                        if is_node is not None:
                            val = "".join([t_el.text for t_el in is_node.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t_el.text])
                    
                    if val is not None and str(val).strip():
                        cols[col_letter] = str(val).strip()

                    # Mapear hiperlink se houver na célula
                    if r in sheet_hyperlinks:
                        cols[f"{col_letter}_link"] = sheet_hyperlinks[r]
                
                if any(cols.values()):
                    rows_data.append((r_idx, cols))
            return rows_data
