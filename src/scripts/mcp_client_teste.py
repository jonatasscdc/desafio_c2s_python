# src/scripts/mcp_client_teste.py
import requests # Biblioteca para fazer requisições HTTP
import json

# URL do servidor FastAPI (certifique-se de que o servidor esteja rodando)
SERVER_URL = "http://127.0.0.1:8000/api/v1/automoveis/buscar"

def testar_busca_sem_filtros():
    print("\n--- Testando busca sem filtros (primeira página) ---")
    payload = {
        "filtros": {}, # Sem filtros específicos
        "paginacao": {"pagina": 1, "itens_por_pagina": 5}
    }
    try:
        response = requests.post(SERVER_URL, json=payload)
        response.raise_for_status() # Levanta um erro para respostas 4xx/5xx
        
        print("Status da Resposta:", response.status_code)
        response_data = response.json()
        print("Resposta JSON:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        
        if response_data.get("sucesso") and response_data.get("dados"):
            print(f"Total de automóveis encontrados: {response_data['dados']['total_encontrado']}")
            print(f"Automóveis na página: {len(response_data['dados']['automoveis'])}")
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
    except json.JSONDecodeError:
        print("Erro ao decodificar resposta JSON. Resposta recebida:")
        print(response.text)


def testar_busca_com_filtros():
    print("\n--- Testando busca com filtros (Marca: Fiat, Ano Máx: 2020) ---")
    payload = {
        "filtros": {
            "marca": "Fiat",
            "ano_max": 2020,
            "tipo_combustivel": "Flex"
        },
        "paginacao": {"pagina": 1, "itens_por_pagina": 3}
    }
    try:
        response = requests.post(SERVER_URL, json=payload)
        response.raise_for_status()
        
        print("Status da Resposta:", response.status_code)
        response_data = response.json()
        print("Resposta JSON:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        if response_data.get("sucesso") and response_data.get("dados"):
            print(f"Total de automóveis encontrados com filtro: {response_data['dados']['total_encontrado']}")
            for carro in response_data['dados']['automoveis']:
                print(f"  - {carro['marca']} {carro['modelo']} ({carro['ano_fabricacao']}) - R${carro['preco']:.2f}")

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
    except json.JSONDecodeError:
        print("Erro ao decodificar resposta JSON. Resposta recebida:")
        print(response.text)

def testar_busca_filtros_sem_resultado():
    print("\n--- Testando busca com filtros que não retornam resultados ---")
    payload = {
        "filtros": {
            "marca": "MarcaInexistenteSuperUltra",
        }
        # Usa paginação padrão se não especificada
    }
    try:
        response = requests.post(SERVER_URL, json=payload)
        response.raise_for_status()
        
        print("Status da Resposta:", response.status_code)
        response_data = response.json()
        print("Resposta JSON:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")

if __name__ == "__main__":
    # Primeiro, garanta que o servidor FastAPI esteja rodando em outro terminal:
    # poetry run uvicorn src.services.mcp_server:app --reload

    print("Iniciando testes do cliente MCP...")
    testar_busca_sem_filtros()
    testar_busca_com_filtros()
    testar_busca_filtros_sem_resultado()
    print("\nTestes do cliente MCP finalizados.")