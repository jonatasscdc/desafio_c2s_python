# tests/services/test_mcp_server.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Any, AsyncGenerator # Adicionado AsyncGenerator
from contextlib import asynccontextmanager # Importar para o decorador
from sqlalchemy.pool import StaticPool

# Importar a app FastAPI e os modelos/configurações de DB
from src.services.mcp_server import app, get_db as original_fastapi_get_db # get_db da app
from src.core.database import Base, AutomovelDB # Não precisamos de OriginalSessionLocal ou create_db_and_tables aqui
from src.models.automovel_model import TipoCombustivelEnum, TipoTransmissaoEnum

# --- Configuração do Banco de Dados de Teste ---
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:" # Banco de dados em memória para testes

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# --- Sobrescrita de Dependências e Lifespan para Testes ---

# Sobrescrever a dependência get_db da aplicação FastAPI para usar a sessão de teste
def override_get_db_for_testing() -> Generator[Session, None, None]: # get_db original é síncrona
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Aplicar a sobrescrita ANTES que o TestClient seja instanciado
app.dependency_overrides[original_fastapi_get_db] = override_get_db_for_testing

# Neutralizar a lifespan da aplicação principal para testes,
# pois nossas fixtures de teste cuidarão da criação/limpeza do banco de teste.
@asynccontextmanager # Decorador correto
async def no_op_lifespan(app_lifespan: Any) -> AsyncGenerator[None, None]: # Tipo de retorno correto
    print("Lifespan da aplicação principal neutralizada para testes (fixture).")
    yield # Um gerador assíncrono precisa de pelo menos um yield
    # Nenhuma lógica de cleanup necessária aqui para o no_op

app.router.lifespan_context = no_op_lifespan


# --- Fixtures Pytest ---

@pytest.fixture(scope="session", autouse=True)
def setup_test_database_tables_once_for_session():
    """
    Cria todas as tabelas no banco de dados de teste em memória UMA VEZ por sessão de teste.
    Isto é essencial para que as tabelas existam quando os testes começarem.
    O autouse=True garante que seja executado automaticamente.
    """
    print("\n[FIXTURE SESSION SCOPE - INÍCIO] Criando todas as tabelas no engine_test...")
    Base.metadata.create_all(bind=engine_test) # Cria tabelas usando o engine_test
    yield
    print("\n[FIXTURE SESSION SCOPE - FIM] Sessão de teste encerrada.")
    # Para sqlite:///:memory:, o banco é descartado ao final da conexão/sessão.
    # Se fosse um arquivo, Base.metadata.drop_all(bind=engine_test) seria mais explícito aqui.

@pytest.fixture(scope="function")
def db_session_for_test() -> Generator[Session, None, None]:
    """
    Fornece uma sessão de banco de dados para um teste e garante que as tabelas
    estejam limpas ANTES de cada teste (isolamento de dados).
    """
    print("\n[FIXTURE FUNCTION SCOPE - db_session_for_test - INÍCIO] Dropando e criando tabelas...")
    # Garantir que as tabelas existam antes de cada teste
    Base.metadata.create_all(bind=engine_test)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        print("[FIXTURE FUNCTION SCOPE - db_session_for_test - FIM] Fechando sessão.")
        db.close()

@pytest.fixture(scope="function")
def client(db_session_for_test: Session) -> Generator[TestClient, None, None]: # Garante que o DB está pronto via dependência da fixture
    """
    Fornece uma instância do TestClient. Depende de db_session_for_test
    para garantir que a configuração do banco (limpeza/criação) ocorreu.
    """
    print("[FIXTURE FUNCTION SCOPE - client - INÍCIO] Criando TestClient.")
    # A substituição de dependência (get_db) e neutralização da lifespan já estão ativas na 'app'
    tc = TestClient(app)
    yield tc
    print("[FIXTURE FUNCTION SCOPE - client - FIM] TestClient usado.")


# --- Testes ---

def test_buscar_automoveis_sem_filtros_retorna_lista_vazia_em_db_limpo(client: TestClient, db_session_for_test: Session):
    """Testa busca sem filtros em um banco de dados de teste limpo."""
    # A fixture db_session_for_test já garantiu que o DB está limpo e tabelas criadas.
    response = client.post("/api/v1/automoveis/buscar", json={"filtros": None, "paginacao": {"pagina": 1, "itens_por_pagina": 5}})
    assert response.status_code == 200, f"Resposta inesperada: {response.text}"
    data = response.json()
    assert data["sucesso"] is True
    assert data["dados"]["automoveis"] == [], f"Esperava lista vazia, obteve: {data['dados']['automoveis']}"
    assert data["dados"]["total_encontrado"] == 0

def test_buscar_automoveis_com_dados_e_filtros(client: TestClient, db_session_for_test: Session):
    """Testa a busca com dados e filtros específicos."""
    carro1 = AutomovelDB(
        marca="TesteMarcaA", modelo="ModeloX", ano_fabricacao=2020, ano_modelo=2020,
        cor="Azul", motorizacao=1.0, tipo_combustivel=TipoCombustivelEnum.FLEX,
        quilometragem=1000, numero_portas=4, transmissao=TipoTransmissaoEnum.MANUAL, preco=50000.0
    )
    carro2 = AutomovelDB(
        marca="TesteMarcaA", modelo="ModeloY", ano_fabricacao=2022, ano_modelo=2022,
        cor="Vermelho", motorizacao=1.6, tipo_combustivel=TipoCombustivelEnum.GASOLINA,
        quilometragem=500, numero_portas=2, transmissao=TipoTransmissaoEnum.AUTOMATICO, preco=70000.0
    )
    carro3 = AutomovelDB(
        marca="OutraMarca", modelo="ModeloZ", ano_fabricacao=2021, ano_modelo=2021,
        cor="Preto", motorizacao=1.8, tipo_combustivel=TipoCombustivelEnum.DIESEL,
        quilometragem=2000, numero_portas=4, transmissao=TipoTransmissaoEnum.MANUAL, preco=90000.0
    )
    db_session_for_test.add_all([carro1, carro2, carro3])
    db_session_for_test.commit()

    response_marca = client.post("/api/v1/automoveis/buscar", json={"filtros": {"marca": "TesteMarcaA"}})
    assert response_marca.status_code == 200, f"Resposta inesperada: {response_marca.text}"
    data_marca = response_marca.json()
    assert data_marca["sucesso"] is True
    assert data_marca["dados"]["total_encontrado"] == 2
    assert len(data_marca["dados"]["automoveis"]) == 2

    response_ano = client.post("/api/v1/automoveis/buscar", json={"filtros": {"ano_min": 2022}})
    assert response_ano.status_code == 200, f"Resposta inesperada: {response_ano.text}"
    data_ano = response_ano.json()
    assert data_ano["sucesso"] is True
    assert data_ano["dados"]["total_encontrado"] == 1
    assert data_ano["dados"]["automoveis"][0]["modelo"] == "ModeloY"

    response_vazio = client.post("/api/v1/automoveis/buscar", json={"filtros": {"marca": "MarcaInexistente"}})
    assert response_vazio.status_code == 200, f"Resposta inesperada: {response_vazio.text}"
    data_vazio = response_vazio.json()
    assert data_vazio["sucesso"] is True
    assert data_vazio["dados"]["total_encontrado"] == 0

def test_buscar_automoveis_valida_filtros_malformados(client: TestClient, db_session_for_test: Session):
    response = client.post("/api/v1/automoveis/buscar", json={"filtros": {"ano_min": "ano_errado"}})
    assert response.status_code == 422, f"Resposta inesperada: {response.text}"
    data = response.json()
    assert "detail" in data
    # A asserção exata para o erro de Pydantic pode variar, mas verificamos a estrutura.
    assert any("Input should be a valid integer" in item.get("msg","") and item.get("loc", []) == ["body", "filtros", "ano_min"] for item in data["detail"])


def test_buscar_automoveis_filtro_preco_min_e_max(client: TestClient, db_session_for_test: Session):
    carro_preco_ok = AutomovelDB(marca="PrecoTeste", modelo="FaixaOk", ano_fabricacao=2020, ano_modelo=2020, cor="Verde", motorizacao=1.0, tipo_combustivel=TipoCombustivelEnum.FLEX, quilometragem=100, numero_portas=4, transmissao=TipoTransmissaoEnum.MANUAL, preco=35000.0)
    carro_preco_baixo = AutomovelDB(marca="PrecoTeste", modelo="FaixaBaixo", ano_fabricacao=2020, ano_modelo=2020, cor="Amarelo", motorizacao=1.0, tipo_combustivel=TipoCombustivelEnum.FLEX, quilometragem=100, numero_portas=4, transmissao=TipoTransmissaoEnum.MANUAL, preco=25000.0)
    carro_preco_alto = AutomovelDB(marca="PrecoTeste", modelo="FaixaAlto", ano_fabricacao=2020, ano_modelo=2020, cor="Laranja", motorizacao=1.0, tipo_combustivel=TipoCombustivelEnum.FLEX, quilometragem=100, numero_portas=4, transmissao=TipoTransmissaoEnum.MANUAL, preco=45000.0)
    db_session_for_test.add_all([carro_preco_ok, carro_preco_baixo, carro_preco_alto])
    db_session_for_test.commit()

    payload = {"filtros": {"marca": "PrecoTeste", "preco_min": 30000.0, "preco_max": 40000.0}}
    response = client.post("/api/v1/automoveis/buscar", json=payload)
    assert response.status_code == 200, f"Resposta inesperada: {response.text}"
    data = response.json()
    assert data["sucesso"] is True
    assert data["dados"]["total_encontrado"] == 1
    assert data["dados"]["automoveis"][0]["modelo"] == "FaixaOk"
    assert data["dados"]["automoveis"][0]["preco"] == 35000.0