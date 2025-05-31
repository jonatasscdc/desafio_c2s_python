# src/core/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum as SQLAlchemyEnum, Uuid as SQLAlchemyUuid
from sqlalchemy.orm import sessionmaker, declarative_base
import uuid
from datetime import datetime

# Importar nossos Enums do Pydantic para reutilizar no SQLAlchemy
# Isso garante consistência entre a validação e o armazenamento
from src.models.automovel_model import TipoCombustivelEnum, TipoTransmissaoEnum

# Definindo o caminho para o arquivo do banco de dados SQLite
# Ele será criado na pasta 'data/' na raiz do projeto
DATABASE_URL = "sqlite:///./data/automoveis.db"

# create_engine é o ponto de partida para qualquer aplicação SQLAlchemy.
# O 'connect_args' é específico para SQLite e necessário para
# habilitar o suporte a multithreading de forma segura.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# sessionmaker cria uma fábrica de sessões. Uma sessão gerencia todas
# as operações de persistência para os objetos ORM.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# declarative_base() retorna uma classe base da qual todos os modelos
# mapeados (nossas tabelas) devem herdar.
Base = declarative_base()

# Modelo SQLAlchemy para Automovel
class AutomovelDB(Base):
    __tablename__ = "automoveis"

    # Colunas da tabela
    id_veiculo = Column(SQLAlchemyUuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marca = Column(String(50), nullable=False, index=True)
    modelo = Column(String(50), nullable=False, index=True)
    ano_fabricacao = Column(Integer, nullable=False)
    ano_modelo = Column(Integer, nullable=False)
    cor = Column(String(30), nullable=False)
    motorizacao = Column(Float, nullable=False)
    # Usamos SQLAlchemyEnum para mapear nosso Enum Python para o banco
    tipo_combustivel = Column(SQLAlchemyEnum(TipoCombustivelEnum, name="tipocombustivelenum"), nullable=False)
    quilometragem = Column(Integer, nullable=False)
    numero_portas = Column(Integer, nullable=False)
    transmissao = Column(SQLAlchemyEnum(TipoTransmissaoEnum, name="tipotransmissaoenum"), nullable=False)
    preco = Column(Float, nullable=False)
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False)
    observacoes = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<AutomovelDB(marca='{self.marca}', modelo='{self.modelo}', ano='{self.ano_fabricacao}')>"

# Função para criar todas as tabelas no banco de dados
# Esta função será chamada uma vez para configurar o schema do banco.
def create_db_and_tables():
    # Cria a pasta 'data' se ela não existir
    import os
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

# Adicione no src/core/__init__.py:
# from .database import SessionLocal, engine, create_db_and_tables, AutomovelDB
# __all__ = ["SessionLocal", "engine", "create_db_and_tables", "AutomovelDB"]