# src/services/mcp_server.py

from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, and_ # Import 'and_' para múltiplas condições

# Nossos modelos e configuração de banco
from src.models.automovel_model import Automovel as AutomovelPydanticModel, TipoCombustivelEnum, TipoTransmissaoEnum
from src.core.database import SessionLocal, AutomovelDB, engine, create_db_and_tables

from datetime import datetime
from sqlalchemy import func
from pydantic import BaseModel, Field, field_validator # Adicionar field_validator

# --- Modelos Pydantic para Requisição e Resposta da API ---

class FiltrosAutomovel(BaseModel):
    marca: Optional[str] = Field(None, min_length=2, max_length=50)
    modelo: Optional[str] = Field(None, min_length=1, max_length=50)
    ano_min: Optional[int] = Field(None, gt=1900)
    ano_max: Optional[int] = Field(None, lt=datetime.now().year + 3)
    tipo_combustivel: Optional[TipoCombustivelEnum] = None
    preco_max: Optional[float] = Field(None, gt=0)
    # Adicionar mais filtros conforme necessário
    # quilometragem_max: Optional[int] = Field(None, ge=0)
    # transmissao: Optional[TipoTransmissaoEnum] = None

    # Validador para garantir que ano_max >= ano_min se ambos forem fornecidos
    @field_validator('ano_max')
    def validar_ano_max(cls, v, values):
        data = values.data
        if 'ano_min' in data and data['ano_min'] is not None and v is not None and v < data['ano_min']:
            raise ValueError('Ano máximo não pode ser menor que o ano mínimo.')
        return v

class Paginacao(BaseModel):
    pagina: int = Field(1, gt=0)
    itens_por_pagina: int = Field(10, gt=0, le=100) # Limitar itens por página

class MCPRequest(BaseModel):
    filtros: Optional[FiltrosAutomovel] = None
    paginacao: Optional[Paginacao] = Field(default_factory=Paginacao)


class AutomovelRespostaParaAPI(AutomovelPydanticModel): # Herda do nosso modelo Pydantic principal
    # Poderíamos adicionar/omitir campos específicos para a API aqui se necessário
    pass

class MCPDadosResposta(BaseModel):
    automoveis: List[AutomovelRespostaParaAPI]
    total_encontrado: int
    pagina_atual: int
    total_paginas: int

class MCPResponse(BaseModel):
    sucesso: bool
    mensagem: str
    dados: Optional[MCPDadosResposta] = None
    erros: Optional[Dict[str, str]] = None


# --- Configuração da Aplicação FastAPI ---
app = FastAPI(
    title="API de Busca de Automóveis C2S",
    description="API para buscar automóveis com base em filtros (Protocolo MCP)",
    version="0.1.0"
)

# --- Dependência para obter a sessão do banco de dados ---
def get_db():
    db = SessionLocal()
    try:
        yield db # Fornece a sessão para a rota
    finally:
        db.close() # Fecha a sessão após a requisição ser processada

# --- Evento de Inicialização da Aplicação (para criar tabelas, se necessário) ---
@app.on_event("startup")
def on_startup():
    print("Servidor FastAPI iniciando...")
    print("Verificando e criando tabelas do banco de dados, se necessário...")
    create_db_and_tables() # Garante que as tabelas existam
    print("Tabelas verificadas/criadas.")
    print("Servidor pronto para aceitar requisições.")


# --- Endpoint da API ---
@app.post("/api/v1/automoveis/buscar", response_model=MCPResponse, tags=["Automóveis"])
async def buscar_automoveis(
    mcp_request: MCPRequest = Body(...), # Recebe o corpo da requisição
    db: Session = Depends(get_db) # Injeção de dependência da sessão do DB
):
    """
    Busca automóveis no banco de dados com base nos filtros fornecidos.
    """
    query_base = select(AutomovelDB)
    condicoes = []

    if mcp_request.filtros:
        filtros = mcp_request.filtros
        if filtros.marca:
            condicoes.append(AutomovelDB.marca.ilike(f"%{filtros.marca}%")) # ilike para case-insensitive
        if filtros.modelo:
            condicoes.append(AutomovelDB.modelo.ilike(f"%{filtros.modelo}%"))
        if filtros.ano_min:
            condicoes.append(AutomovelDB.ano_fabricacao >= filtros.ano_min) # ou ano_modelo, decidir
        if filtros.ano_max:
            condicoes.append(AutomovelDB.ano_fabricacao <= filtros.ano_max) # ou ano_modelo
        if filtros.tipo_combustivel:
            condicoes.append(AutomovelDB.tipo_combustivel == filtros.tipo_combustivel)
        if filtros.preco_max:
            condicoes.append(AutomovelDB.preco <= filtros.preco_max)
        # Adicionar mais condições de filtro aqui...

    if condicoes:
        query_base = query_base.where(and_(*condicoes)) # Aplica todas as condições com AND

    # Contar o total de resultados antes da paginação
    total_encontrado = db.scalar(select(func.count()).select_from(query_base.order_by(None).subquery()))

    # Paginação
    paginacao = mcp_request.paginacao if mcp_request.paginacao else Paginacao()
    offset = (paginacao.pagina - 1) * paginacao.itens_por_pagina
    query_base = query_base.offset(offset).limit(paginacao.itens_por_pagina)
    
    # Ordenação (opcional, pode ser adicionada)
    query_base = query_base.order_by(AutomovelDB.marca, AutomovelDB.modelo, AutomovelDB.ano_fabricacao.desc())

    try:
        resultados_db = db.execute(query_base).scalars().all()
    except Exception as e:
        # Logar o erro `e` aqui em um ambiente de produção
        print(f"Erro ao consultar o banco: {e}") # Para debug
        raise HTTPException(status_code=500, detail="Erro interno ao processar a busca.")

    # Converter resultados SQLAlchemy para modelos Pydantic para a resposta
    automoveis_resposta = [AutomovelRespostaParaAPI.model_validate(auto_db) for auto_db in resultados_db]
    
    total_paginas = (total_encontrado + paginacao.itens_por_pagina - 1) // paginacao.itens_por_pagina if total_encontrado > 0 else 0
    if paginacao.pagina > total_paginas and total_encontrado > 0 :
         # Se a página pedida for maior que o total de páginas existentes (e houver resultados)
         # Isso pode acontecer se, por exemplo, o usuário estava na última página e itens foram removidos.
         # Poderíamos retornar um erro ou a última página válida. Por ora, vamos retornar lista vazia para a página inválida.
         # Ou melhor, vamos ajustar a mensagem e retornar a primeira página, ou um erro claro.
         # Para simplificar, se a página pedida não tem resultados mas o total_encontrado > 0, 
         # significa que a página é inválida. Retornaremos sucesso mas lista vazia.
         # No entanto, o cálculo de total_paginas já deve lidar com isso.
         pass


    dados_resposta = MCPDadosResposta(
        automoveis=automoveis_resposta,
        total_encontrado=total_encontrado,
        pagina_atual=paginacao.pagina,
        total_paginas=total_paginas
    )

    return MCPResponse(
        sucesso=True,
        mensagem="Busca realizada com sucesso." if automoveis_resposta else "Nenhum automóvel encontrado com os filtros fornecidos.",
        dados=dados_resposta
    )

# Para rodar este servidor:
# No terminal, na raiz do projeto: poetry run uvicorn src.services.mcp_server:app --reload
# O '--reload' é para desenvolvimento, reinicia o servidor quando o código muda.