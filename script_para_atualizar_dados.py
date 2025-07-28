import json
import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os

# --- Configuração ---
OUTPUT_FILE = "painel_de_vagas.html"
TEMPLATE_FILE = "template.html"
GEOJSON_FILE = "dados/brazil.geojson"
MUNICIPIOS_COORDS_FILE = "dados/municipios_brasileiros.json"

TARGET_URLS = [
    "https://www.pciconcursos.com.br/cargos/administrador/",
    "https://www.pciconcursos.com.br/cargos/agente-administrativo/",
    "https://www.pciconcursos.com.br/cargos/assistente-administrativo/",
    "https://www.pciconcursos.com.br/cargos/auxiliar-administrativo/",
    "https://www.pciconcursos.com.br/cargos/controlador-interno/",
    "https://www.pciconcursos.com.br/cargos/oficial-administrativo/",
    "https://www.pciconcursos.com.br/cargos/tecnico-administrativo/",
    "https://www.pciconcursos.com.br/cargos/psicologo/",
]

# --- Funções Auxiliares ---

def load_file_content(filepath: str) -> str | None:
    """Carrega o conteúdo de um arquivo de texto (HTML, JSON, etc)."""
    if not os.path.exists(filepath):
        print(f"❌ ERRO: Arquivo não encontrado em '{filepath}'")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError as e:
        print(f"❌ ERRO: Falha ao ler o arquivo '{filepath}': {e}")
        return None

def get_uf_from_string(text: str) -> str:
    """Extrai a sigla do estado (UF) do final de uma string."""
    match = re.search(r'\s-\s([A-Z]{2})$', text.strip())
    if match:
        return match.group(1)
    match_parenteses = re.search(r'\(([A-Z]{2})\)$', text.strip())
    if match_parenteses:
        return match_parenteses.group(1)
    return 'N/D'

def scrape_vagas(url: str, ids_vagas_existentes: set, municipios_data: dict) -> list:
    """
    Extrai informações de vagas usando a lógica validada de leitura sequencial
    (.link-d para órgãos e .link-i para cargos).
    """
    print(f"   > Extraindo de: {url}")
    vagas_encontradas = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        nodes = soup.select('#pagina .link-d, #pagina .link-i')
        
        current_orgao = {'text': 'N/A', 'href': '#'}

        for node in nodes:
            if 'link-d' in node.get('class', []):
                link = node.select_one('a')
                if link and link.get_text(strip=True):
                    href = link.get('href', '#')
                    full_href = f"https://www.pciconcursos.com.br{href}" if href.startswith('/') else href
                    current_orgao = {'text': link.get_text(strip=True), 'href': full_href}
            
            elif 'link-i' in node.get('class', []):
                link = node.select_one('a')
                if link:
                    cargo_text = link.get_text(strip=True)
                    id_vaga = f"{current_orgao['text']}|{cargo_text}"
                    
                    if id_vaga not in ids_vagas_existentes:
                        uf = get_uf_from_string(current_orgao['text'])
                        municipio = "N/D"
                        
                        if uf != 'N/D':
                            orgao_lower = current_orgao['text'].lower()
                            possible_municipios = [k for k in municipios_data if k.endswith(f'-{uf.lower()}')]
                            for key in possible_municipios:
                                municipio_key = key.rsplit('-', 1)[0]
                                if municipio_key in orgao_lower:
                                    municipio = municipio_key.replace("-", " ").title()
                                    break

                        vaga_data = {
                            'orgao': current_orgao['text'],
                            'link_orgao': current_orgao['href'],
                            'cargo': cargo_text,
                            'uf': uf,
                            'municipio': municipio
                        }
                        vagas_encontradas.append(vaga_data)
                        ids_vagas_existentes.add(id_vaga)

    except requests.RequestException as e:
        print(f"   ! Erro de conexão ao acessar a URL {url}: {e}")
    except Exception as e:
        print(f"   ! Ocorreu um erro inesperado ao processar {url}: {e}")

    return vagas_encontradas

def main():
    """Função principal para orquestrar o scraping e a geração do HTML."""
    start_time = time.time()
    print("🚀 Iniciando script de atualização de vagas...")
    print("--------------------------------------------------")

    # Carrega arquivos
    print("📄 Carregando arquivos de dados e template...")
    html_template = load_file_content(TEMPLATE_FILE)
    brazil_geojson_str = load_file_content(GEOJSON_FILE)
    municipios_coords_str = load_file_content(MUNICIPIOS_COORDS_FILE)
    
    if not all([html_template, brazil_geojson_str, municipios_coords_str]):
        print("\n❌ Script interrompido devido à falta de arquivos essenciais.")
        return
        
    municipios_coords = json.loads(municipios_coords_str)
    
    print("✅ Arquivos carregados com sucesso.")
    print("--------------------------------------------------")

    # Inicia extração
    print("🕸️  Iniciando extração de vagas...")
    todas_as_vagas = []
    ids_vagas_unicas = set()
    for url in TARGET_URLS:
        vagas_da_url = scrape_vagas(url, ids_vagas_unicas, municipios_coords)
        todas_as_vagas.extend(vagas_da_url)
        time.sleep(1) # Pausa amigável
    print("--------------------------------------------------")
    print(f"✨ Extração finalizada. Total de {len(todas_as_vagas)} vagas únicas encontradas.")

    # Prepara os dados para o template
    data_extracao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    final_data = {
        "vagas": todas_as_vagas,
        "total_vagas": len(todas_as_vagas),
        "data_extracao": data_extracao,
    }

    # Injeta os dados no template
    print("🔄 Gerando arquivo HTML final...")
    output_html = html_template.replace("__DATA_PLACEHOLDER__", json.dumps(final_data, ensure_ascii=False))
    output_html = output_html.replace("__GEOJSON_PLACEHOLDER__", brazil_geojson_str)
    output_html = output_html.replace("__MUNICIPIOS_COORDS_PLACEHOLDER__", municipios_coords_str)

    # Salva o arquivo final
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output_html)
        end_time = time.time()
        print("--------------------------------------------------")
        print(f"✅ Sucesso! O arquivo '{OUTPUT_FILE}' foi gerado em {end_time - start_time:.2f} segundos.")
    except IOError as e:
        print(f"❌ ERRO CRÍTICO: Não foi possível escrever o arquivo '{OUTPUT_FILE}': {e}")

if __name__ == "__main__":
    main()
