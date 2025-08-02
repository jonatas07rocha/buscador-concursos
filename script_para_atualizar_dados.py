import json
import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
import unicodedata

# --- Configuração ---
# O script agora gera um arquivo JSON com os dados das vagas.
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
        # Normaliza para decompor acentos e caracteres
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    except TypeError:
        pass
    return text.lower()

def load_file_content(filepath: str) -> str | None:
    """Carrega o conteúdo de um arquivo de texto (JSON, etc.)."""
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

def save_vagas_to_json(data: dict, filename: str):
    """
    Salva os dados extraídos em um arquivo JSON formatado.
    Garante que o diretório de destino exista antes de salvar.
    """
    print(f"🔄 Gerando arquivo JSON final em '{filename}'...")
    try:
        # Garante que o diretório de saída exista
        output_dir = os.path.dirname(filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        with open(filename, "w", encoding="utf-8") as f:
            # Usa indent=4 para um arquivo JSON legível
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Sucesso! O arquivo '{filename}' foi gerado.")
    except IOError as e:
        print(f"❌ ERRO CRÍTICO: Não foi possível escrever o arquivo '{filename}': {e}")

def scrape_vagas(url: str, ids_vagas_existentes: set, municipios_data: dict) -> list:
    """
    Extrai informações de vagas usando a lógica validada de leitura sequencial
    e uma busca aprimorada por municípios.
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
                        
                        # Lógica de busca de município
                        if uf != 'N/D':
                            orgao_normalizado = normalize_text(current_orgao['text'])
                            possible_municipios = [k for k in municipios_data if k.endswith(f'-{uf.lower()}')]
                            for key in possible_municipios:
                                municipio_key_sem_uf = key.rsplit('-', 1)[0]
                                termo_busca = municipio_key_sem_uf.replace('-', ' ')
                                if termo_busca in orgao_normalizado:
                                    municipio = termo_busca.title()
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
    """Função principal para orquestrar o scraping e a geração do arquivo JSON."""
    start_time = time.time()
    print("🚀 Iniciando script de atualização de vagas...")
    print("--------------------------------------------------")

    # Carrega arquivos
    print("📄 Carregando arquivo de coordenadas dos municípios...")
    municipios_coords_str = load_file_content(MUNICIPIOS_COORDS_FILE)
    
    if not municipios_coords_str:
        print("\n❌ Script interrompido devido à falta do arquivo de municípios.")
        return
        
    municipios_coords = json.loads(municipios_coords_str)
    
    print("✅ Arquivo carregado com sucesso.")
    print("--------------------------------------------------")

    # Inicia extração
    print("🕸️  Iniciando extração de vagas...")
    todas_as_vagas = []
    ids_vagas_unicas = set()
    for url in TARGET_URLS:
        vagas_da_url = scrape_vagas(url, ids_vagas_unicas, municipios_coords)
        todas_as_vagas.extend(vagas_da_url)
        time.sleep(1) # Pausa amigável para não sobrecarregar o servidor
        
    print("--------------------------------------------------")
    print(f"✨ Extração finalizada. Total de {len(todas_as_vagas)} vagas únicas encontradas.")

    # Prepara os dados para o arquivo JSON
    final_data = {
        "data_extracao": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
        "total_vagas": len(todas_as_vagas),
        "vagas": todas_as_vagas,
    }

    # Salva o arquivo final no formato JSON
    save_vagas_to_json(final_data, OUTPUT_FILE)
    
    end_time = time.time()
    print("--------------------------------------------------")
    print(f"✅ Script finalizado em {end_time - start_time:.2f} segundos.")


if __name__ == "__main__":
    main()