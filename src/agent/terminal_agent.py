# src/agent/terminal_agent.py
import requests
import json
import re # Para expressões regulares

from src.models.automovel_model import TipoCombustivelEnum # Para validar/sugerir

SERVER_URL = "http://127.0.0.1:8000/api/v1/automoveis/buscar" # Mesma do cliente

# Marcas conhecidas para facilitar a extração
MARCAS_CONHECIDAS = ["fiat", "volkswagen", "chevrolet", "ford", "hyundai", "toyota", "renault", "honda", "jeep", "nissan", "peugeot", "citroen", "bmw", "mercedes", "audi"]

def extrair_entidades(texto_usuario: str, slots_atuais: dict) -> dict:
    """
    Tenta extrair entidades relevantes do texto do usuário.
    Abordagem MUITO simples baseada em palavras-chave e regex.
    """
    texto_lower = texto_usuario.lower()
    novos_slots = slots_atuais.copy() # Não modificar os slots originais diretamente aqui

    # 1. Extrair Marca
    if not novos_slots.get("marca"): # Só extrai se ainda não tivermos uma marca
        for marca in MARCAS_CONHECIDAS:
            if marca in texto_lower:
                novos_slots["marca"] = marca.capitalize() # Armazena com a primeira letra maiúscula
                # Remover a marca do texto para evitar que seja confundida com modelo
                texto_lower = texto_lower.replace(marca, "").strip()
                break # Pega a primeira marca encontrada

    # 2. Extrair Ano (simples regex para 4 dígitos entre 1900-20XX)
    # Consideraremos o primeiro ano encontrado como ano_min por simplicidade
    # Se houver "até ANO", "antes de ANO", consideraremos ano_max
    # Se houver "depois de ANO", "a partir de ANO", consideraremos ano_min
    anos_encontrados = re.findall(r'\b(19\d{2}|20\d{2})\b', texto_lower)
    if anos_encontrados:
        anos_numericos = sorted([int(ano) for ano in anos_encontrados])
        if not novos_slots.get("ano_min") and not novos_slots.get("ano_max"): # Se nenhum ano foi definido
            if len(anos_numericos) == 1:
                # Se "até ANO" ou "antes de ANO"
                if any(term in texto_lower for term in ["ate", "antes de", "maximo de", "menos de"]):
                    novos_slots["ano_max"] = anos_numericos[0]
                else: # Caso contrário, assume como ano específico (ou ano mínimo)
                    novos_slots["ano_min"] = anos_numericos[0]
                    # Poderia também definir ano_max se for uma busca por ano específico.
                    # Para simplicidade, o servidor já pode tratar ano_min=X e ano_max=X.
            elif len(anos_numericos) >= 2:
                novos_slots["ano_min"] = anos_numericos[0]
                novos_slots["ano_max"] = anos_numericos[-1]
    
    # 3. Extrair Tipo de Combustível
    if not novos_slots.get("tipo_combustivel"):
        for combustivel in TipoCombustivelEnum:
            if combustivel.value.lower() in texto_lower:
                novos_slots["tipo_combustivel"] = combustivel.value
                break
    
    # 4. Extrair Preço Máximo (ex: "até 50000", "menos de 30 mil")
    if not novos_slots.get("preco_max"):
        match_preco = re.search(r'(?:ate|maximo de|menos de|por menos de)\s*R?\$\s*([\d\.]+)(?:\s*mil)?', texto_lower, re.IGNORECASE)
        if match_preco:
            preco_str = match_preco.group(1).replace('.', '')
            preco = float(preco_str)
            if "mil" in match_preco.group(0).lower(): # Se a palavra "mil" estiver presente
                preco *= 1000
            novos_slots["preco_max"] = preco

    # 5. Extrair Modelo (muito simplista: o que sobrou e não é stopword comum)
    # Esta é a parte mais frágil sem NLU avançado.
    if novos_slots.get("marca") and not novos_slots.get("modelo"):
        # Remove termos comuns e o que já foi identificado
        palavras_restantes = texto_lower
        if novos_slots.get("tipo_combustivel"):
            palavras_restantes = palavras_restantes.replace(novos_slots["tipo_combustivel"].lower(), "")
        
        # Remove anos já capturados
        for ano_str_re in re.findall(r'\b(19\d{2}|20\d{2})\b', palavras_restantes):
            palavras_restantes = palavras_restantes.replace(ano_str_re, "")

        # Remove termos de preço
        palavras_restantes = re.sub(r'(?:ate|maximo de|menos de|por menos de)\s*R?\$\s*([\d\.]+)(?:\s*mil)?', "", palavras_restantes, flags=re.IGNORECASE)

        # Remove algumas stopwords comuns e termos de busca
        stopwords = ["quero", "gostaria", "procuro", "um", "uma", "carro", "veiculo", "de", "da", "do", "com", "sem", "para", "e", "ou", "me", "acha", "encontra"]
        for sw in stopwords:
            palavras_restantes = palavras_restantes.replace(f" {sw} ", " ").strip()
        
        modelo_candidato = palavras_restantes.strip()
        if modelo_candidato and len(modelo_candidato.split()) <= 2 and len(modelo_candidato) > 1: # Modelo com 1 ou 2 palavras
            # Evitar pegar apenas números ou restos de palavras-chave
            if not modelo_candidato.isdigit() and modelo_candidato not in ["mil", "r$"]:
                novos_slots["modelo"] = modelo_candidato.capitalize()
    
    return novos_slots


def apresentar_resultados(automoveis: list):
    if not automoveis:
        print("\n😕 Puxa, não encontrei nenhum carro com esses critérios.")
        return

    print(f"\n🎉 Encontrei {len(automoveis)} carro(s) para você:")
    for i, carro in enumerate(automoveis):
        print(f"\n--- Opção {i+1} ---")
        print(f"  Marca: {carro.get('marca', 'N/A')}")
        print(f"  Modelo: {carro.get('modelo', 'N/A')}")
        print(f"  Ano Fabricação/Modelo: {carro.get('ano_fabricacao', 'N/A')}/{carro.get('ano_modelo', 'N/A')}")
        print(f"  Cor: {carro.get('cor', 'N/A')}")
        print(f"  Motor: {carro.get('motorizacao', 'N/A')}L")
        print(f"  Combustível: {carro.get('tipo_combustivel', 'N/A')}")
        print(f"  Transmissão: {carro.get('transmissao', 'N/A')}")
        print(f"  Quilometragem: {carro.get('quilometragem', 'N/A')} km")
        print(f"  Preço: R$ {carro.get('preco', 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) # Formato BR
    print("-" * 20)


def interagir_com_servidor(slots_coletados: dict) -> list:
    """Envia os filtros para o servidor e retorna a lista de automóveis."""
    payload_filtros = {}
    if slots_coletados.get("marca"):
        payload_filtros["marca"] = slots_coletados["marca"]
    if slots_coletados.get("modelo"):
        payload_filtros["modelo"] = slots_coletados["modelo"]
    if slots_coletados.get("ano_min"):
        payload_filtros["ano_min"] = slots_coletados["ano_min"]
    if slots_coletados.get("ano_max"):
        payload_filtros["ano_max"] = slots_coletados["ano_max"]
    if slots_coletados.get("tipo_combustivel"):
        payload_filtros["tipo_combustivel"] = slots_coletados["tipo_combustivel"]
    if slots_coletados.get("preco_max"):
        payload_filtros["preco_max"] = slots_coletados["preco_max"]

    if not payload_filtros: # Se nenhum filtro útil foi extraído
        print("🤔 Não consegui identificar filtros na sua solicitação para buscar.")
        # Poderia pedir para o usuário tentar de novo ou ser mais específico
        # Por ora, se não houver filtros, podemos buscar tudo (ou os primeiros X)
        # Ou podemos decidir que pelo menos um filtro é necessário.
        # Para este exemplo, vamos buscar tudo se nenhum filtro for extraído.
        # O servidor já tem uma paginação padrão.
        pass


    payload_mcp = {
        "filtros": payload_filtros,
        "paginacao": {"pagina": 1, "itens_por_pagina": 5} # Pegar os 5 primeiros resultados
    }

    print(f"\n🕵️ Buscando com os seguintes filtros: {payload_filtros if payload_filtros else 'todos os carros'}...")
    
    try:
        response = requests.post(SERVER_URL, json=payload_mcp)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("sucesso") and response_data.get("dados"):
            return response_data["dados"].get("automoveis", [])
        else:
            print(f"❌ Erro do servidor: {response_data.get('mensagem', 'Não foi possível obter os dados.')}")
            if response_data.get("erros"):
                print(f"   Detalhes: {response_data['erros']}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"🔌 Ops! Não consegui me conectar ao servidor de busca: {e}")
        return []
    except json.JSONDecodeError:
        print("📋 Erro ao processar a resposta do servidor (não era JSON válido).")
        return []


def iniciar_conversa():
    print("👋 Olá! Sou seu agente virtual de busca de carros.")
    print("Como posso te ajudar a encontrar um veículo hoje? (Ex: 'quero um Fiat Uno até 30000')")
    
    slots = {
        "marca": None, "modelo": None, "ano_min": None, "ano_max": None, 
        "tipo_combustivel": None, "preco_max": None
    }
    campos_necessarios_para_busca_automatica = 1 # Pelo menos 1 filtro para buscar automaticamente

    while True:
        entrada_usuario = input("\nVocê: ").strip()
        if not entrada_usuario:
            print("Por favor, me diga o que você procura.")
            continue

        if entrada_usuario.lower() in ["sair", "exit", "fim", "tchau"]:
            print("Até logo! 👋")
            break

        # Tentar extrair entidades da nova entrada
        slots = extrair_entidades(entrada_usuario, slots)
        
        print(f"ℹ️ Entendi até agora: Marca: {slots['marca']}, Modelo: {slots['modelo']}, Ano Min: {slots['ano_min']}, Ano Max: {slots['ano_max']}, Combustível: {slots['tipo_combustivel']}, Preço Máx: {slots['preco_max']}")

        # Lógica de perguntas para preencher slots faltantes
        # Esta parte pode ser expandida para ser mais inteligente
        
        filtros_preenchidos = sum(1 for val in slots.values() if val is not None)

        if entrada_usuario.lower() == "buscar" or "buscar agora" in entrada_usuario.lower() or "procurar" in entrada_usuario.lower():
            if filtros_preenchidos > 0:
                automoveis = interagir_com_servidor(slots)
                apresentar_resultados(automoveis)
                # Resetar slots para nova busca ou refinar? Por ora, vamos resetar.
                slots = {k: None for k in slots} 
                print("\nO que mais posso fazer por você? (Ou digite 'sair')")
            else:
                print("Por favor, me dê alguns detalhes do que você procura antes de pedir para buscar.")
            continue


        if not slots["marca"]:
            print("Agente: Qual marca de carro você tem em mente?")
            continue # Volta para pegar a próxima entrada do usuário
        
        # Se já temos uma marca, mas não muitos outros filtros, podemos perguntar mais.
        if filtros_preenchidos < 2 and not slots["preco_max"] : # Exemplo de condição para mais perguntas
             print("Agente: Alguma faixa de preço específica ou ano de preferência?")
             continue
        
        # Se o usuário forneceu vários detalhes de uma vez, ou se já temos alguns filtros
        if filtros_preenchidos >= campos_necessarios_para_busca_automatica:
            print("Agente: Entendido. Você gostaria de buscar com esses critérios ou adicionar mais alguma informação? (digite 'buscar' ou forneça mais detalhes)")
            # Não buscamos automaticamente aqui, esperamos o usuário confirmar com 'buscar' ou adicionar mais.
        else:
             print("Agente: Pode me dar mais alguns detalhes? Como ano, tipo de combustível ou faixa de preço?")