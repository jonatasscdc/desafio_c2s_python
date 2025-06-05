# tests/models/test_automovel_model.py
import pytest
from pydantic import ValidationError
from uuid import UUID
from datetime import datetime

# As importações de Automovel já usarão a versão com ConfigDict
from src.models.automovel_model import Automovel, TipoCombustivelEnum, TipoTransmissaoEnum

def test_automovel_criacao_valida():
    """Testa a criação de um Automovel com dados válidos."""
    agora = datetime.now()
    dados_validos = {
        "marca": "Fiat",
        "modelo": "Uno",
        "ano_fabricacao": 2020,
        "ano_modelo": 2021,
        "cor": "Branco",
        "motorizacao": 1.0,
        "tipo_combustivel": TipoCombustivelEnum.FLEX,
        "quilometragem": 30000,
        "numero_portas": 4,
        "transmissao": TipoTransmissaoEnum.MANUAL,
        "preco": 45000.00,
    }
    auto = Automovel(**dados_validos)
    assert auto.marca == "Fiat"
    assert isinstance(auto.id_veiculo, UUID)
    assert isinstance(auto.data_cadastro, datetime)
    # Ajustar a comparação de data_cadastro para ser menos frágil
    assert (agora - auto.data_cadastro).total_seconds() < 5 # Dentro de 5 segundos

def test_automovel_ano_fabricacao_invalido():
    """Testa validação de ano_fabricacao muito antigo."""
    dados = {
        "marca": "Ford", "modelo": "Modelo T", "ano_fabricacao": 1899, "ano_modelo": 1900,
        "cor": "Preto", "motorizacao": 2.0, "tipo_combustivel": "Gasolina",
        "quilometragem": 100000, "numero_portas": 2, "transmissao": "Manual", "preco": 5000.0
    }
    with pytest.raises(ValidationError) as excinfo:
        Automovel(**dados)
    # Verificar se o erro é sobre 'ano_fabricacao' e a regra 'gt'
    assert any(err['type'] == 'greater_than' and err['loc'] == ('ano_fabricacao',) for err in excinfo.value.errors())

def test_automovel_ano_modelo_menor_que_fabricacao():
    """Testa validação customizada: ano_modelo < ano_fabricacao."""
    dados = {
        "marca": "VW", "modelo": "Gol", "ano_fabricacao": 2022, "ano_modelo": 2021,
        "cor": "Prata", "motorizacao": 1.0, "tipo_combustivel": "Flex",
        "quilometragem": 1000, "numero_portas": 4, "transmissao": "Manual", "preco": 60000.0
    }
    with pytest.raises(ValidationError) as excinfo:
        Automovel(**dados)
    assert any(err['type'] == 'value_error' and 'Ano do modelo deve ser maior ou igual' in err['msg'] for err in excinfo.value.errors())

def test_automovel_preco_negativo():
    """Testa validação de preço negativo."""
    dados = {
        "marca": "Fiat", "modelo": "Mobi", "ano_fabricacao": 2021, "ano_modelo": 2021,
        "cor": "Vermelho", "motorizacao": 1.0, "tipo_combustivel": "Flex",
        "quilometragem": 5000, "numero_portas": 4, "transmissao": "Manual", "preco": -100.0
    }
    with pytest.raises(ValidationError) as excinfo:
        Automovel(**dados)
    assert any(err['type'] == 'greater_than' and err['loc'] == ('preco',) for err in excinfo.value.errors())

def test_automovel_tipo_combustivel_invalido():
    """Testa se um valor inválido para Enum é rejeitado."""
    dados = {
        "marca": "Tesla", "modelo": "Model S", "ano_fabricacao": 2023, "ano_modelo": 2023,
        "cor": "Branco", "motorizacao": 0.0, "tipo_combustivel": "Querosene", # Inválido
        "quilometragem": 100, "numero_portas": 4, "transmissao": "Automático", "preco": 350000.0
    }
    with pytest.raises(ValidationError) as excinfo:
        Automovel(**dados)
    assert any(err['type'] == 'enum' and err['loc'] == ('tipo_combustivel',) for err in excinfo.value.errors())