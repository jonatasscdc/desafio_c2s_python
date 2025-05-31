# src/agent/terminal_agent.py
import requests
import json
import re
import os
from dotenv import load_dotenv # Para carregar variáveis de ambiente

# LangChain e Gemini Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field # Usar Pydantic v2 diretamente
from langchain_core.output_parsers import PydanticOutputParser
from typing import Optional, List

# Importações do nosso projeto
from src.models.automovel_model import TipoCombustivelEnum

# Carregar variáveis de ambiente do arquivo .env que deve estar na raiz do projeto
load_dotenv()

SERVER_URL = "http://127.0.0.1:8000/api/v1/automoveis/buscar"

# --- Definição do Esquema de Saída para o LLM com Pydantic V2 ---
class ExtracaoFiltrosCarro(BaseModel):
    """
    Define a estrutura de dados que esperamos que o LLM extraia
    do texto do usuário sobre as preferências de um carro.
    """
    marca: Optional[str] = Field(default=None, description="A marca do carro mencionada, se houver. Ex: Fiat, Volkswagen.")
    modelo: Optional[str] = Field(default=None, description="O nome ou código alfanumérico do modelo do carro. Ex: Uno, Gol, Corolla, Renegade. Não deve ser apenas um número de ano.")
    ano_min: Optional[int] = Field(default=None, description="O ano mínimo de fabricação desejado, se mencionado. Ex: 2018.")
    ano_max: Optional[int] = Field(default=None, description="O ano máximo de fabricação desejado, se mencionado. Ex: 2022.")
    tipo_combustivel: Optional[str] = Field(default=None, description=f"O tipo de combustível desejado, se mencionado. Se possível, normalize para um dos seguintes: {', '.join([e.value for e in TipoCombustivelEnum])}.")
    preco_min: Optional[float] = Field(default=None, description="O preço mínimo desejado em Reais, se mencionado. Ex: 30000.0.")
    preco_max: Optional[float] = Field(default=None, description="O preço máximo desejado em Reais, se mencionado. Ex: 50000.0.")
    outras_caracteristicas: Optional[List[str]] = Field(default_factory=list, description="Outras características ou palavras-chave relevantes mencionadas pelo usuário que não se encaixam nos campos acima. Ex: novo, usado, vermelho, 4 portas, econômico.")

# --- Função de Extração de Entidades com LLM ---
def extrair_entidades_com_llm(texto_usuario: str, slots_atuais: dict) -> dict:
    """
    Usa um LLM (Gemini via LangChain) para extrair entidades do texto do usuário
    e atualizar os slots.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("\n⚠️  Chave de API do Google (GOOGLE_API_KEY) não encontrada no arquivo .env.")
        print("    Por favor, crie um arquivo .env na raiz do projeto com sua chave.")
        print("    Exemplo: GOOGLE_API_KEY=\"SUA_CHAVE_AQUI\"")
        print("    Retornando aos slots atuais sem extração por LLM.\n")
        return slots_atuais

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=google_api_key, temperature=0.1)
    parser = PydanticOutputParser(pydantic_object=ExtracaoFiltrosCarro)
    lista_combustiveis_str = ", ".join([e.value for e in TipoCombustivelEnum])

    prompt_template_str = """
    Sua tarefa é analisar a solicitação de um usuário que está procurando um carro e extrair os critérios de busca.
    Preencha os campos do JSON de saída com as informações extraídas.
    Se uma informação não for explicitamente mencionada pelo usuário, deixe o campo correspondente como nulo ou omita-o.
    Não invente informações. Seja o mais fiel possível ao que o usuário disse.

    Instruções específicas para os campos:
    - 'marca': A fabricante do veículo (ex: Fiat, Chevrolet).
    - 'modelo': O nome ou código específico do veículo dentro da marca (ex: Uno, Onix, Renegade). O campo 'modelo' NÃO deve ser preenchido com um número de ano. Se o usuário mencionar apenas um ano e uma marca, o campo 'modelo' deve permanecer nulo, a menos que um nome de modelo seja claramente identificável.
    - 'ano_min', 'ano_max': Anos de fabricação. Se o usuário mencionar um único ano (ex: "carro de 2019"), interprete-o como ano_min = 2019 e ano_max = 2019, a menos que termos como "a partir de", "desde" (para ano_min) ou "até", "antes de" (para ano_max) especifiquem uma faixa.
    - 'tipo_combustivel': Se mencionado, normalize para um dos seguintes valores: {lista_combustiveis}.
    - 'preco_min', 'preco_max': Valores de preço em Reais. Converta para float (ex: "30 mil" para 30000.0, "entre R$20k e R$25.000" para preco_min=20000.0 e preco_max=25000.0).
    - 'outras_caracteristicas': Uma lista de outras palavras-chave ou atributos mencionados (ex: cor, número de portas, "econômico", "novo").

    TEXTO DO USUÁRIO:
    "{texto_do_usuario}"

    FILTROS JÁ COLETADOS ANTERIORMENTE (se houver algum valor, tente não sobrescrevê-lo a menos que o usuário esteja claramente corrigindo ou especificando algo novo para esse mesmo filtro):
    Marca atual: {marca_atual}
    Modelo atual: {modelo_atual}
    Ano mínimo atual: {ano_min_atual}
    Ano máximo atual: {ano_max_atual}
    Tipo de combustível atual: {tipo_combustivel_atual}
    Preço mínimo atual: {preco_min_atual}
    Preço máximo atual: {preco_max_atual}

    INSTRUÇÕES DE FORMATAÇÃO (siga estritamente):
    {format_instructions}
    """

    prompt = ChatPromptTemplate.from_template(
        template=prompt_template_str,
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
            "lista_combustiveis": lista_combustiveis_str
        }
    )

    chain = prompt | llm | parser

    print("\n🤖 Consultando o Gemini para entender sua solicitação...")
    try:
        contexto_slots = {
            "marca_atual": slots_atuais.get("marca") or "não definido",
            "modelo_atual": slots_atuais.get("modelo") or "não definido",
            "ano_min_atual": slots_atuais.get("ano_min") or "não definido",
            "ano_max_atual": slots_atuais.get("ano_max") or "não definido",
            "tipo_combustivel_atual": slots_atuais.get("tipo_combustivel") or "não definido",
            "preco_min_atual": slots_atuais.get("preco_min") or "não definido",
            "preco_max_atual": slots_atuais.get("preco_max") or "não definido",
        }

        input_data_for_llm = {
            "texto_do_usuario": texto_usuario,
            **contexto_slots
        }

        resultado_llm: ExtracaoFiltrosCarro = chain.invoke(input_data_for_llm)
        novos_slots = slots_atuais.copy()

        # Lógica de Pós-Processamento para o campo 'modelo'
        if resultado_llm.modelo and resultado_llm.modelo.isdigit() and len(resultado_llm.modelo) == 4:
            is_year_min = resultado_llm.ano_min and int(resultado_llm.modelo) == resultado_llm.ano_min
            is_year_max = resultado_llm.ano_max and int(resultado_llm.modelo) == resultado_llm.ano_max
            if is_year_min or is_year_max:
                print(f"   ℹ️ Corrigindo: LLM colocou o ano '{resultado_llm.modelo}' como modelo. Removendo do modelo.")
                resultado_llm.modelo = None

        for campo, valor_llm in resultado_llm.model_dump().items():
            if valor_llm is not None:
                if campo == "outras_caracteristicas" and not valor_llm:
                    continue
                if campo in novos_slots:
                    if novos_slots[campo] is None or (novos_slots[campo] != valor_llm and campo != "outras_caracteristicas"):
                        if campo == "tipo_combustivel":
                            try:
                                valor_llm_str = str(valor_llm)
                                if not any(v == valor_llm_str for v in TipoCombustivelEnum._value2member_map_):
                                    valor_llm_str = valor_llm_str.capitalize()
                                enum_val = TipoCombustivelEnum(valor_llm_str)
                                novos_slots[campo] = enum_val.value
                                print(f"   LLM atualizou/preencheu '{campo}': {enum_val.value}")
                            except ValueError:
                                print(f"   ⚠️ LLM sugeriu um tipo de combustível inválido ou não normalizado: '{valor_llm}'. Slot não atualizado.")
                        else:
                            novos_slots[campo] = valor_llm
                            print(f"   LLM atualizou/preencheu '{campo}': {valor_llm}")
                    elif campo == "outras_caracteristicas" and valor_llm and novos_slots[campo] != valor_llm :
                        novos_slots[campo] = valor_llm # Substitui lista de outras características
                        print(f"   LLM atualizou/preencheu '{campo}': {valor_llm}")
        return novos_slots
    except Exception as e:
        print(f"❌ Erro crítico ao interagir com o LLM: {e}")
        import traceback
        traceback.print_exc()
        print("Retornando aos slots atuais.")
        return slots_atuais

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
        print(f"  Preço: R$ {carro.get('preco', 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print("-" * 20)

def interagir_com_servidor(slots_coletados: dict) -> list:
    payload_filtros = {}
    campos_permitidos_servidor = ["marca", "modelo", "ano_min", "ano_max", "tipo_combustivel", "preco_max", "preco_min"]
    for campo, valor in slots_coletados.items():
        if valor is not None and campo in campos_permitidos_servidor:
            # Para campos de lista como 'outras_caracteristicas', não incluímos diretamente
            # a menos que o servidor tenha um campo específico para eles.
            if not isinstance(valor, list):
                 payload_filtros[campo] = valor

    payload_mcp = {
        "filtros": payload_filtros if payload_filtros else None,
        "paginacao": {"pagina": 1, "itens_por_pagina": 5}
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
            if response_data.get("erros"): print(f"   Detalhes: {response_data['erros']}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"🔌 Ops! Não consegui me conectar ao servidor de busca: {e}")
        return []
    except json.JSONDecodeError:
        print("📋 Erro ao processar a resposta do servidor (não era JSON válido). Resposta:")
        print(response.text if 'response' in locals() else "N/A")
        return []

def iniciar_conversa():
    print("👋 Olá! Sou seu agente virtual de busca de carros (com Gemini!).")
    print("Como posso te ajudar a encontrar um veículo hoje? (Ex: 'quero um Fiat Uno até 30000', 'Chevrolet Onix 2019 flex')")
    slots = {
        "marca": None, "modelo": None, "ano_min": None, "ano_max": None,
        "tipo_combustivel": None, "preco_min": None, "preco_max": None,
        "outras_caracteristicas": []
    }
    while True:
        entrada_usuario = input("\nVocê: ").strip()
        if not entrada_usuario and not any(value for key, value in slots.items() if key != "outras_caracteristicas" and value is not None): # Se entrada vazia E nenhum filtro real preenchido
            print("Por favor, me diga o que você procura ou forneça alguns detalhes.")
            continue

        if entrada_usuario.lower() in ["sair", "exit", "fim", "tchau", "quit", "parar"]:
            print("Até logo! 👋")
            break

        if entrada_usuario or not any(value for key, value in slots.items() if key != "outras_caracteristicas" and value is not None): # Processa se houver entrada ou se nenhum filtro útil
            slots = extrair_entidades_com_llm(entrada_usuario, slots)

        feedback_slots = {k: v for k, v in slots.items() if v is not None and (not isinstance(v, list) or v)}
        if feedback_slots:
            feedback_str = ", ".join([f"{k.replace('_', ' ').capitalize()}: {v}" for k,v in feedback_slots.items()])
            print(f"ℹ️ Entendi até agora: {feedback_str}")
        elif entrada_usuario : # Se houve entrada mas o LLM não pegou nada útil
            print("ℹ️ Humm, não consegui extrair filtros específicos dessa vez. Pode tentar de novo ou ser mais detalhado?")


        filtros_reais_preenchidos_count = sum(1 for k, val in slots.items() if k != "outras_caracteristicas" and val is not None and (not isinstance(val, list) or val) )

        if entrada_usuario.lower() in ["buscar", "procurar"] or (not entrada_usuario and filtros_reais_preenchidos_count > 0):
            automoveis = interagir_com_servidor(slots)
            apresentar_resultados(automoveis)
            print("\nO que mais posso fazer por você? (Forneça mais detalhes, 'buscar' novamente, ou 'sair')")
            continue

        if filtros_reais_preenchidos_count == 0 and entrada_usuario:
            print("Agente: Humm, não entendi bem. Pode tentar descrever de outra forma o carro que você busca?")
        elif entrada_usuario:
            print("Agente: Ok. Adicione mais detalhes se quiser, ou digite 'buscar' para ver os resultados.")