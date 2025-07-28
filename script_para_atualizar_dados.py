import json
import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

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

def clean_text(text):
    """Remove espaços em branco extras do início e do fim de uma string."""
    return text.strip()

def load_data_file(filepath):
    """Carrega dados de um arquivo, tratando possíveis erros."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if filepath.endswith('.json'):
                return json.load(f)
            return f.read()
    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo essencial '{filepath}' não foi encontrado.")
        print("   Por favor, verifique se o arquivo existe no local correto e tente novamente.")
        return None
    except json.JSONDecodeError:
        print(f"❌ ERRO: O arquivo JSON '{filepath}' está mal formatado ou é inválido.")
        return None

def scrape_vagas(url):
    """Extrai as informações de vagas de uma URL do PCI Concursos."""
    print(f"   > Extraindo de: {url}")
    vagas = []
    try:
        # Define um cabeçalho User-Agent para simular um navegador real
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        vagas_elements = soup.find_all('div', class_='ca')

        for vaga_element in vagas_elements:
            link_element = vaga_element.a
            # Validação mais robusta para encontrar os elementos corretos
            if not link_element: continue
            orgao_element = link_element.find_next_sibling('a')
            if not orgao_element: continue
            local_text_element = orgao_element.find_next_sibling(string=True)
            if not local_text_element: continue

            cargo = clean_text(link_element.text)
            link_orgao = link_element.get('href', '')
            orgao = clean_text(orgao_element.text)

            local_match = re.search(r"([^\(]+)\s+\((.+)\)", clean_text(local_text_element))
            if local_match:
                municipio = clean_text(local_match.group(1))
                uf = clean_text(local_match.group(2).replace(")", ""))
                vagas.append({
                    "cargo": cargo,
                    "orgao": orgao,
                    "municipio": municipio,
                    "uf": uf,
                    "link_orgao": f"https://www.pciconcursos.com.br{link_orgao}"
                })
    except requests.exceptions.RequestException as e:
        print(f"   ! Erro de rede ao acessar a URL {url}: {e}")
    except Exception as e:
        print(f"   ! Ocorreu um erro inesperado ao processar {url}: {e}")

    return vagas

def main():
    """Função principal para orquestrar o scraping e a geração do HTML."""
    start_time = time.time()
    
    print("📂 Carregando arquivos de dados e template...")
    
    # Carrega todos os arquivos necessários no início
    html_template = load_data_file(TEMPLATE_FILE)
    municipios_coords = load_data_file(MUNICIPIOS_COORDS_FILE)
    brazil_geojson = load_data_file(GEOJSON_FILE)

    # Se qualquer arquivo essencial não for carregado, interrompe a execução
    if not all([html_template, municipios_coords, brazil_geojson]):
        print("\n🛑 Execução interrompida devido à falta de arquivos essenciais.")
        return

    print("✅ Arquivos carregados com sucesso.")
    
    print("\n🕸️  Iniciando extração de vagas...")
    todas_as_vagas = []
    for url in TARGET_URLS:
        vagas_da_url = scrape_vagas(url)
        todas_as_vagas.extend(vagas_da_url)
        time.sleep(1.5) # Pausa maior para ser mais gentil com o servidor

    print(f"\n✨ Extração finalizada. Total de {len(todas_as_vagas)} vagas encontradas.")

    data_extracao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

    final_data = {
        "vagas": todas_as_vagas,
        "total_vagas": len(todas_as_vagas),
        "data_extracao": data_extracao,
    }

    print("📄 Gerando arquivo HTML final...")
    
    # Substitui os placeholders no template
    output_html = html_template.replace("__DATA_PLACEHOLDER__", json.dumps(final_data, ensure_ascii=False))
    output_html = output_html.replace("__GEOJSON_PLACEHOLDER__", brazil_geojson)
    output_html = output_html.replace("__MUNICIPIOS_COORDS_PLACEHOLDER__", json.dumps(municipios_coords, ensure_ascii=False))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output_html)

    end_time = time.time()
    print(f"\n🚀 Sucesso! O arquivo '{OUTPUT_FILE}' foi gerado em {end_time - start_time:.2f} segundos.")


if __name__ == "__main__":
    main()
