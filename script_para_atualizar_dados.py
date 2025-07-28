import json
import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os

# --- Configuração ---
OUTPUT_FILE = "painel_de_vagas.html"
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

def carregar_dados_json(caminho_arquivo: str):
    """Carrega dados de um arquivo JSON e retorna um dicionário."""
    if not os.path.exists(caminho_arquivo):
        print(f"❌ ERRO: O arquivo de dados '{caminho_arquivo}' não foi encontrado.")
        return None
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ ERRO: Falha ao ler ou decodificar o arquivo '{caminho_arquivo}': {e}")
        return None

def carregar_template_html(caminho_arquivo: str) -> str | None:
    """Carrega o conteúdo de um arquivo de template HTML."""
    if not os.path.exists(caminho_arquivo):
        print(f"❌ ERRO: O arquivo de template '{caminho_arquivo}' não foi encontrado.")
        return None
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError as e:
        print(f"❌ ERRO: Falha ao ler o arquivo de template '{caminho_arquivo}': {e}")
        return None

def get_uf_from_string(text: str) -> str:
    """Extrai a sigla do estado (UF) do final de uma string de órgão."""
    # Procura por " - UF" no final da string
    match = re.search(r'\s-\s([A-Z]{2})$', text.strip())
    if match:
        return match.group(1)
    
    # Fallback para " (UF)" no final, caso o padrão mude
    match_parenteses = re.search(r'\(([A-Z]{2})\)$', text.strip())
    if match_parenteses:
        return match_parenteses.group(1)
        
    return 'N/D'

def scrape_vagas(url: str, ids_vagas_existentes: set, municipios_coords: dict) -> list:
    """
    Extrai informações de vagas de uma URL do PCI Concursos, focando na estrutura
    correta das páginas de cargos e usando uma lógica robusta para identificar o município.
    """
    print(f"   > Extraindo de: {url}")
    vagas_encontradas = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # A estrutura correta nas páginas de cargo é uma 'div' com a classe 'ca'
        vaga_elements = soup.find_all('div', class_='ca')
        
        for element in vaga_elements:
            links = element.find_all('a')
            if len(links) < 2:
                continue

            cargo_text = links[0].get_text(strip=True)
            orgao_text = links[1].get_text(strip=True)
            link_concurso = f"https://www.pciconcursos.com.br{links[1].get('href', '#')}"
            
            id_vaga = f"{orgao_text}|{cargo_text}"
            if id_vaga in ids_vagas_existentes:
                continue

            uf = get_uf_from_string(orgao_text)
            municipio_encontrado = "N/D"

            if uf != 'N/D':
                # Lógica para encontrar o município de forma mais confiável
                orgao_lower = orgao_text.lower()
                # Filtra os municípios da UF correspondente para otimizar a busca
                possible_municipios = [k for k in municipios_coords if k.endswith(f'-{uf.lower()}')]
                for key in possible_municipios:
                    municipio_key = key.rsplit('-', 1)[0]
                    if municipio_key in orgao_lower:
                        municipio_encontrado = municipio_key.title()
                        break
            
            vaga_data = {
                'orgao': orgao_text,
                'cargo': cargo_text,
                'link_orgao': link_concurso,
                'uf': uf,
                'municipio': municipio_encontrado
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

    # Carrega arquivos de dados e template
    print("📄 Carregando arquivos de dados e template...")
    municipios_coords = carregar_dados_json('dados/municipios_brasileiros.json')
    brazil_geojson = carregar_dados_json('dados/brazil.geojson')
    html_template = carregar_template_html('template.html')

    if not all([municipios_coords, brazil_geojson, html_template]):
        print("\n❌ Script interrompido devido à falta de arquivos essenciais.")
        return
    print("✅ Arquivos carregados com sucesso.")
    print("--------------------------------------------------")

    # Inicia extração
    print("🕸️  Iniciando extração de vagas...")
    todas_as_vagas = []
    ids_vagas_unicas = set() # Garante vagas únicas em toda a execução
    for url in TARGET_URLS:
        # Passa a lista de coordenadas para a função de scraping
        vagas_da_url = scrape_vagas(url, ids_vagas_unicas, municipios_coords)
        todas_as_vagas.extend(vagas_da_url)
        time.sleep(1) # Pausa para não sobrecarregar o servidor
    print("--------------------------------------------------")
    print(f"✨ Extração finalizada. Total de {len(todas_as_vagas)} vagas encontradas.")

    # Prepara os dados finais para o template
    data_extracao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    final_data = {
        "vagas": todas_as_vagas,
        "total_vagas": len(todas_as_vagas),
        "data_extracao": data_extracao,
    }

    # Injeta os dados no template
    print("🔄 Gerando arquivo HTML final...")
    output_html = html_template.replace("__DATA_PLACEHOLDER__", json.dumps(final_data, ensure_ascii=False))
    output_html = output_html.replace("__GEOJSON_PLACEHOLDER__", json.dumps(brazil_geojson, ensure_ascii=False))
    output_html = output_html.replace("__MUNICIPIOS_COORDS_PLACEHOLDER__", json.dumps(municipios_coords, ensure_ascii=False))

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
