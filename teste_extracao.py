import requests
from bs4 import BeautifulSoup
import re

# --- CONFIGURAÇÃO DO TESTE ---
# Vamos usar apenas uma URL como nosso "grupo de controle"
URL_CONTROLE = "https://www.pciconcursos.com.br/cargos/psicologo/"

def get_uf_from_string(text: str) -> str:
    """Extrai a sigla do estado (UF) do final de uma string."""
    match = re.search(r'\s-\s([A-Z]{2})$', text.strip())
    if match:
        return match.group(1)
    match_parenteses = re.search(r'\(([A-Z]{2})\)$', text.strip())
    if match_parenteses:
        return match_parenteses.group(1)
    return 'N/D'

def testar_extracao():
    """
    Função de teste que usa a lógica correta (baseada em .link-d e .link-i)
    para validar a extração de dados.
    """
    print(f"🕵️  Iniciando teste de extração com a lógica CORRIGIDA:")
    print(f"🔗 URL: {URL_CONTROLE}")
    print("--------------------------------------------------")
    
    vagas_encontradas = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(URL_CONTROLE, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # LÓGICA CORRETA: Seleciona todos os links de órgãos e de vagas na ordem
        nodes = soup.select('#pagina .link-d, #pagina .link-i')
        
        print(f"✅ Conexão bem-sucedida. {len(nodes)} nós (órgãos/vagas) encontrados na página.")
        print("--------------------------------------------------")

        orgao_atual = "N/A"
        
        for node in nodes:
            # Se o nó é um órgão, atualiza o nome do órgão atual
            if 'link-d' in node.get('class', []):
                link_orgao = node.select_one('a')
                if link_orgao and link_orgao.get_text(strip=True):
                    orgao_atual = link_orgao.get_text(strip=True)
            
            # Se o nó é uma vaga, processa a vaga com o último órgão encontrado
            elif 'link-i' in node.get('class', []):
                link_cargo = node.select_one('a')
                if link_cargo:
                    cargo_text = link_cargo.get_text(strip=True)
                    uf = get_uf_from_string(orgao_atual)
                    
                    vaga_data = {
                        'orgao': orgao_atual,
                        'cargo': cargo_text,
                        'uf': uf
                    }
                    vagas_encontradas.append(vaga_data)

    except requests.RequestException as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")
        return
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")
        return

    # Imprime os resultados encontrados
    if vagas_encontradas:
        print(f"🎉 SUCESSO! {len(vagas_encontradas)} vagas extraídas:")
        for i, vaga in enumerate(vagas_encontradas[:15], 1): # Mostra as 15 primeiras
            print(f"   {i:02d}. [UF: {vaga['uf']}] {vaga['orgao']} -> Cargo: {vaga['cargo']}")
        if len(vagas_encontradas) > 15:
            print(f"   ... e mais {len(vagas_encontradas) - 15} vagas.")
    else:
        print("🤔 Nenhuma vaga foi extraída. A estrutura do site pode ter mudado.")
    
    print("--------------------------------------------------")
    print("Teste finalizado.")

if __name__ == "__main__":
    testar_extracao()
