import json
import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
import unicodedata

# --- Configuração ---
OUTPUT_FILE = "dados/vagas.json" 
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

def normalize_text(text: str) -> str:
    """Remove acentos, caracteres especiais e converte para minúsculas."""
    try:
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    except (TypeError, AttributeError):
        return ""
    return text.lower().strip()

def load_file_content(filepath: str) -> str | None:
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
    match = re.search(r'\s-\s([A-Z]{2})$', text.strip())
    if match:
        return match.group(1)
    match_parenteses = re.search(r'\(([A-Z]{2})\)$', text.strip())
    if match_parenteses:
        return match_parenteses.group(1)
    return 'N/D'

def save_vagas_to_json(data: dict, filename: str):
    print(f"🔄 Gerando arquivo JSON final em '{filename}'...")
    try:
        output_dir = os.path.dirname(filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ Sucesso! O arquivo '{filename}' foi gerado.")
    except IOError as e:
        print(f"❌ ERRO CRÍTICO: Não foi possível escrever o arquivo '{filename}': {e}")

def find_municipio_and_coords(orgao_text: str, link_orgao: str, uf: str, municipios_data: dict) -> tuple:
    """
    Lógica aprimorada para encontrar o município e suas coordenadas.
    Tenta encontrar no nome do órgão e também na URL do link.
    """
    municipio_encontrado = "N/D"
    lat, lng = None, None
    
    if uf == 'N/D':
        return municipio_encontrado, lat, lng

    possible_municipios = [k for k, v in municipios_data.items() if v.get('uf', '').lower() == uf.lower()]
    
    # Concatena os textos onde a busca será feita para maior abrangência
    text_to_search_in = normalize_text(orgao_text) + " " + normalize_text(link_orgao)
    
    # Prioriza municípios com mais palavras para evitar correspondências erradas (ex: "Silva" em "Silva Jardim")
    possible_municipios.sort(key=lambda name: len(name.split('-')), reverse=True)

    found_key = None
    for key in possible_municipios:
        municipio_key_sem_uf = key.rsplit('-', 1)[0]
        termo_busca = municipio_key_sem_uf.replace('-', ' ')
        
        if termo_busca in text_to_search_in:
            municipio_encontrado = termo_busca.title()
            found_key = key
            break

    if found_key and found_key in municipios_data:
        coords = municipios_data[found_key]
        lat = coords.get("lat")
        lng = coords.get("lon")
        
    return municipio_encontrado, lat, lng

def scrape_vagas(url: str, ids_vagas_existentes: set, municipios_data: dict) -> list:
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
                        
                        municipio, lat, lng = find_municipio_and_coords(
                            current_orgao['text'], 
                            current_orgao['href'], 
                            uf, 
                            municipios_data
                        )

                        vaga_data = {
                            'orgao': current_orgao['text'],
                            'link_orgao': current_orgao['href'],
                            'cargo': cargo_text,
                            'uf': uf,
                            'municipio': municipio,
                            'lat': lat,
                            'lng': lng
                        }
                        vagas_encontradas.append(vaga_data)
                        ids_vagas_existentes.add(id_vaga)

    except requests.RequestException as e:
        print(f"   ! Erro de conexão ao acessar a URL {url}: {e}")
    except Exception as e:
        print(f"   ! Ocorreu um erro inesperado ao processar {url}: {e}")

    return vagas_encontradas

def main():
    start_time = time.time()
    print("🚀 Iniciando script de atualização de vagas...")
    print("--------------------------------------------------")
    print("📄 Carregando arquivo de coordenadas dos municípios...")
    
    municipios_coords_str = load_file_content(MUNICIPIOS_COORDS_FILE)
    if not municipios_coords_str:
        print("\n❌ Script interrompido devido à falta do arquivo de municípios.")
        return
        
    # Transforma o JSON de { "lat": ..., "lon": ..., "nome": ..., "uf": ... } para { "nome-uf": {lat:..., lon:...} }
    raw_municipios = json.loads(municipios_coords_str)
    municipios_data = {
        f"{normalize_text(mun['nome']).replace(' ', '-')}-{mun['uf'].lower()}": {
            "lat": mun.get("latitude"), 
            "lon": mun.get("longitude"),
            "uf": mun.get("uf")
        }
        for mun in raw_municipios
    }
    
    print("✅ Arquivo de coordenadas carregado e processado.")
    print("--------------------------------------------------")

    print("🕸️  Iniciando extração de vagas...")
    todas_as_vagas = []
    ids_vagas_unicas = set()
    for url in TARGET_URLS:
        vagas_da_url = scrape_vagas(url, ids_vagas_unicas, municipios_data)
        todas_as_vagas.extend(vagas_da_url)
        time.sleep(1) 
        
    print("--------------------------------------------------")
    print(f"✨ Extração finalizada. Total de {len(todas_as_vagas)} vagas únicas encontradas.")

    final_data = {
        "data_extracao": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
        "total_vagas": len(todas_as_vagas),
        "vagas": todas_as_vagas,
    }

    save_vagas_to_json(final_data, OUTPUT_FILE)
    
    end_time = time.time()
    print("--------------------------------------------------")
    print(f"✅ Script finalizado em {end_time - start_time:.2f} segundos.")

if __name__ == "__main__":
    main()