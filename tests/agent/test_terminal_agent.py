# tests/agent/test_terminal_agent.py
import pytest
from unittest import mock
import requests # Para mockar requests.exceptions.RequestException

from src.agent.terminal_agent import (
    extrair_entidades_com_llm,
    interagir_com_servidor,
    apresentar_resultados,
    ExtracaoFiltrosCarro # O modelo Pydantic que o LLM deve retornar
)
from src.models.automovel_model import TipoCombustivelEnum # Para construir mocks

# --- Testes para extrair_entidades_com_llm (com Mock do LLM) ---

@mock.patch('src.agent.terminal_agent.os.getenv')                 # 4. mock_getenv_func
@mock.patch('src.agent.terminal_agent.ChatPromptTemplate')      # 3. mock_chat_prompt_template_class
@mock.patch('src.agent.terminal_agent.ChatGoogleGenerativeAI')  # 2. mock_chat_google_class
@mock.patch('src.agent.terminal_agent.PydanticOutputParser')    # 1. mock_pydantic_parser_class
def test_extrair_entidades_com_llm_simples(
    mock_pydantic_parser_class: mock.MagicMock,    # Argumento para o patch 1 (PydanticOutputParser)
    mock_chat_google_class: mock.MagicMock,        # Argumento para o patch 2 (ChatGoogleGenerativeAI)
    mock_chat_prompt_template_class: mock.MagicMock, # Argumento para o patch 3 (ChatPromptTemplate)
    mock_getenv_func: mock.MagicMock               # Argumento para o patch 4 (os.getenv)
    ):
    """Testa a extração de entidades mockando o resultado final da cadeia LangChain."""

    # 1. Simular que a chave de API existe
    mock_getenv_func.return_value = "DUMMY_API_KEY"

    # 2. Definir o objeto ExtracaoFiltrosCarro que esperamos que a cadeia retorne
    mock_resposta_llm_parseada = ExtracaoFiltrosCarro(
        marca="Fiat",
        modelo="Uno",
        ano_min=2020,
        ano_max=2020,
        preco_max=30000.0,
        tipo_combustivel=TipoCombustivelEnum.FLEX.value,
        outras_caracteristicas=[] # Importante definir todos os campos
    )

    # 3. Configurar os mocks da cadeia LangChain:
    # A cadeia é: chain = prompt | llm | parser
    # O resultado final de chain.invoke() é o que parser.invoke(resultado_do_llm) retorna.

    # Mock da instância do PydanticOutputParser e seu método invoke (ou parse)
    # Este é o mock CRUCIAL, pois é o resultado final da cadeia.
    mock_parser_instance = mock_pydantic_parser_class.return_value # PydanticOutputParser(...)
    mock_parser_instance.invoke.return_value = mock_resposta_llm_parseada # parser.invoke(...)

    # Mock da instância do ChatGoogleGenerativeAI e seu método invoke
    mock_llm_instance = mock_chat_google_class.return_value # ChatGoogleGenerativeAI(...)
    # O LLM retorna um objeto tipo BaseMessage. O parser.invoke o consome.
    # Como parser.invoke já está mockado, o que o LLM retorna aqui não é usado para o resultado final,
    # mas precisa ser um mock para a cadeia não quebrar.
    mock_llm_instance.invoke.return_value = mock.MagicMock(content="Conteúdo JSON mockado que o parser (real) consumiria")

    # Mock da instância do ChatPromptTemplate (retornado por from_template) e seu método invoke
    mock_prompt_object = mock.MagicMock() # O objeto prompt retornado por from_template
    mock_prompt_object.invoke.return_value = {"dummy_input_para_llm": "valor"} # O que o prompt.invoke() retorna para o LLM
    mock_chat_prompt_template_class.from_template.return_value = mock_prompt_object

    # Mock da cadeia completa para duplo encadeamento (prompt | llm | parser)
    mock_chain = mock.MagicMock()
    mock_chain.invoke.return_value = mock_resposta_llm_parseada

    # O prompt | llm retorna um objeto intermediário, que ao receber | parser retorna mock_chain
    mock_prompt_llm = mock.MagicMock()
    mock_prompt_llm.__or__.return_value = mock_chain
    # prompt | llm
    mock_prompt_object.__or__.return_value = mock_prompt_llm
    # mock_chat_prompt_template_class.from_template retorna mock_prompt_object (já feito acima)
    
    # Slots iniciais para o teste
    slots_iniciais = {
        "marca": None, "modelo": None, "ano_min": None, "ano_max": None,
        "tipo_combustivel": None, "preco_min": None, "preco_max": None,
        "outras_caracteristicas": []
    }
    texto_usuario_teste = "Quero um Fiat Uno 2020 flex até 30000"
    
    # Chamar a função a ser testada
    slots_atualizados = extrair_entidades_com_llm(texto_usuario_teste, slots_iniciais.copy())

    # Asserções
    assert slots_atualizados.get("marca") == "Fiat", f"Esperado 'Fiat', mas obtido {slots_atualizados.get('marca')}"
    assert slots_atualizados.get("modelo") == "Uno", f"Esperado 'Uno', mas obtido {slots_atualizados.get('modelo')}"
    assert slots_atualizados.get("ano_min") == 2020, f"Esperado 2020, mas obtido {slots_atualizados.get('ano_min')}"
    assert slots_atualizados.get("ano_max") == 2020, f"Esperado 2020, mas obtido {slots_atualizados.get('ano_max')}"
    assert slots_atualizados.get("preco_max") == 30000.0, f"Esperado 30000.0, mas obtido {slots_atualizados.get('preco_max')}"
    assert slots_atualizados.get("tipo_combustivel") == TipoCombustivelEnum.FLEX.value, f"Esperado {TipoCombustivelEnum.FLEX.value}, mas obtido {slots_atualizados.get('tipo_combustivel')}"
    assert slots_atualizados.get("preco_min") is None, f"Esperado None para preco_min, mas obtido {slots_atualizados.get('preco_min')}"


# --- Testes para interagir_com_servidor (mockando requests.post) ---
@mock.patch('src.agent.terminal_agent.requests.post')
def test_interagir_com_servidor_sucesso(mock_post: mock.MagicMock):
    mock_resposta_servidor = {
        "sucesso": True,
        "dados": {
            "automoveis": [{"marca": "Fiat", "modelo": "Uno", "preco": 25000.0}],
            "total_encontrado": 1, "pagina_atual":1, "total_paginas":1
        }
    }
    mock_post.return_value = mock.MagicMock(status_code=200, json=lambda: mock_resposta_servidor)
    slots = {"marca": "Fiat", "modelo": "Uno"}
    resultado = interagir_com_servidor(slots)
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs['json']['filtros']['marca'] == "Fiat"
    assert kwargs['json']['filtros']['modelo'] == "Uno"
    assert len(resultado) == 1
    assert resultado[0]["marca"] == "Fiat"

@mock.patch('src.agent.terminal_agent.requests.post')
def test_interagir_com_servidor_falha_conexao(mock_post: mock.MagicMock):
    mock_post.side_effect = requests.exceptions.RequestException("Falha de conexão mockada")
    slots = {"marca": "Qualquer"}
    resultado = interagir_com_servidor(slots)
    assert resultado == []

# --- Testes para apresentar_resultados (capturando stdout) ---
def test_apresentar_resultados_com_carros(capsys: pytest.CaptureFixture[str]):
    carros = [
        {"marca": "VW", "modelo": "Gol", "ano_fabricacao": 2021, "ano_modelo": 2021, "cor": "Branco", "motorizacao": 1.0, "tipo_combustivel": "Flex", "transmissao": "Manual", "quilometragem": 10000, "preco": 55000.00},
        {"marca": "Ford", "modelo": "Ka", "ano_fabricacao": 2019, "ano_modelo": 2020, "cor": "Preto", "motorizacao": 1.0, "tipo_combustivel": "Gasolina", "transmissao": "Manual", "quilometragem": 25000, "preco": 48000.00}
    ]
    apresentar_resultados(carros)
    captured = capsys.readouterr()
    assert "Encontrei 2 carro(s) para você:" in captured.out
    assert "Marca: VW" in captured.out
    assert "Modelo: Gol" in captured.out
    assert "Preço: R$ 55.000,00" in captured.out
    assert "Marca: Ford" in captured.out

def test_apresentar_resultados_sem_carros(capsys: pytest.CaptureFixture[str]):
    apresentar_resultados([])
    captured = capsys.readouterr()
    assert "Puxa, não encontrei nenhum carro com esses critérios." in captured.out