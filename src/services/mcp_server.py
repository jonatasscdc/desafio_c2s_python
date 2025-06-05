# src/services/mcp_server.py

from fastapi import FastAPI, HTTPException, Body, Depends
# Removido: from fastapi.responses import JSONResponse (não estava sendo usado diretamente)
from pydantic import BaseModel, Field, field_validator, ConfigDict # Adicionado ConfigDict
from typing import List, Optional, Dict, AsyncGenerator # Adicionado AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from contextlib import asynccontextmanager # Para lifespan

from datetime import datetime # Já estava importado, mas garantindo

# Nossos modelos e configuração de banco
from src.models.automovel_model import Automovel as AutomovelPydanticModel, TipoCombustivelEnum, TipoTransmissaoEnum
from src.core.database import SessionLocal, AutomovelDB, engine, create_db_and_tables # SessionLocal é de database.py

from pydantic import ValidationInfo
from typing import Any, Generator

# --- Modelos Pydantic para Requisição e Resposta da API ---

class FiltrosAutomovel(BaseModel):
    model_config = ConfigDict(extra='forbid') # Proibir campos extras na requisição de filtros

    marca: Optional[str] = Field(default=None, min_length=2, max_length=50)
    modelo: Optional[str] = Field(default=None, min_length=1, max_length=50)
    ano_min: Optional[int] = Field(default=None, gt=1900)
    ano_max: Optional[int] = Field(default=None, lt=datetime.now().year + 3)
    tipo_combustivel: Optional[TipoCombustivelEnum] = Field(default=None)
    preco_max: Optional[float] = Field(default=None, gt=0)
    preco_min: Optional[float] = Field(default=None, gt=0) # Adicionando preco_min para o servidor

    @field_validator('ano_max')
    @classmethod
    def validar_ano_max(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        # Assegurar que 'v' e 'ano_min' não sejam None antes de comparar
        if v is not None and 'ano_min' in info.data and info.data['ano_min'] is not None and v < info.data['ano_min']:
            raise ValueError('Ano máximo não pode ser menor que o ano mínimo.')
        return v

    @field_validator('preco_max')
    @classmethod
    def validar_preco_max(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        if v is not None and 'preco_min' in info.data and info.data['preco_min'] is not None and v < info.data['preco_min']:
            raise ValueError('Preço máximo não pode ser menor que o preço mínimo.')
        return v


class Paginacao(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pagina: int = Field(1, gt=0)
    itens_por_pagina: int = Field(10, gt=0, le=100)

class MCPRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    filtros: Optional[FiltrosAutomovel] = Field(default_factory=FiltrosAutomovel) # Default para filtros vazios
    paginacao: Optional[Paginacao] = Field(default_factory=Paginacao)

class AutomovelRespostaParaAPI(AutomovelPydanticModel): # Herda do nosso modelo Pydantic principal
    # model_config já é herdado de AutomovelPydanticModel, que tem from_attributes=True
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
    erros: Optional[Dict[str, Any]] = None # Permitir qualquer tipo de valor para erros detalhados

# --- Gerenciador de Lifespan para eventos de inicialização ---
@asynccontextmanager
async def lifespan(app_lifespan: FastAPI) -> AsyncGenerator[None, None]:
    print("Servidor FastAPI iniciando...")
    print("Verificando e criando tabelas do banco de dados, se necessário...")
    create_db_and_tables() # Garante que as tabelas existam
    print("Tabelas verificadas/criadas.")
    print("Servidor pronto para aceitar requisições.")
    yield
    print("Servidor FastAPI encerrando...")

# --- Configuração da Aplicação FastAPI ---
app = FastAPI(
    title="API de Busca de Automóveis C2S",
    description="API para buscar automóveis com base em filtros (Protocolo MCP)",
    version="0.1.0",
    lifespan=lifespan # Novo gerenciador de lifespan
)

# --- Dependência para obter a sessão do banco de dados ---
def get_db() -> Generator[Session, None, None]: # Corrigido o tipo de retorno
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Removido o evento de startup antigo
# @app.on_event("startup")
# def on_startup(): ...

# --- Endpoint da API ---
@app.post("/api/v1/automoveis/buscar", response_model=MCPResponse, tags=["Automóveis"])
async def buscar_automoveis(
    mcp_request: MCPRequest = Body(default_factory=MCPRequest), # Garante default se corpo vazio
    db: Session = Depends(get_db)
):
    query_base = select(AutomovelDB)
    condicoes = []

    # Usar mcp_request.filtros que agora tem default_factory
    filtros = mcp_request.filtros
    if filtros: # filtros será uma instância de FiltrosAutomovel
        if filtros.marca:
            condicoes.append(AutomovelDB.marca.ilike(f"%{filtros.marca}%"))
        if filtros.modelo:
            condicoes.append(AutomovelDB.modelo.ilike(f"%{filtros.modelo}%"))
        if filtros.ano_min:
            condicoes.append(AutomovelDB.ano_fabricacao >= filtros.ano_min)
        if filtros.ano_max:
            condicoes.append(AutomovelDB.ano_fabricacao <= filtros.ano_max)
        if filtros.tipo_combustivel:
            condicoes.append(AutomovelDB.tipo_combustivel == filtros.tipo_combustivel)
        if filtros.preco_min: # Adicionada condição para preco_min
            condicoes.append(AutomovelDB.preco >= filtros.preco_min)
        if filtros.preco_max:
            condicoes.append(AutomovelDB.preco <= filtros.preco_max)

    if condicoes:
        query_base = query_base.where(and_(*condicoes))

    try:
        # Contagem total
        count_query = select(func.count()).select_from(query_base.order_by(None).alias("subquery_for_count"))
        total_encontrado = db.scalar(count_query) or 0 # Garante 0 se for None

        # Paginação
        paginacao = mcp_request.paginacao # Já tem default_factory
        offset = (paginacao.pagina - 1) * paginacao.itens_por_pagina
        
        # Ordenação (pode ser parametrizada no futuro)
        query_final = query_base.order_by(AutomovelDB.marca, AutomovelDB.modelo, AutomovelDB.ano_fabricacao.desc())
        query_final = query_final.offset(offset).limit(paginacao.itens_por_pagina)
        
        resultados_db = db.execute(query_final).scalars().all()

    except Exception as e:
        print(f"Erro ao consultar o banco: {e}")
        import traceback
        traceback.print_exc()
        # Para erros de validação Pydantic na requisição, FastAPI já retorna 422.
        # Este é para erros inesperados na lógica do banco/servidor.
        # Não vamos usar HTTPException aqui diretamente para não mascarar o traceback nos logs,
        # FastAPI já lida com erros não tratados como 500.
        # Se quiséssemos uma resposta JSON específica para o erro 500, usaríamos:
        # return MCPResponse(sucesso=False, mensagem="Erro interno ao processar a busca.", erros={"detalhe": str(e)})
        # Mas deixar o FastAPI tratar como 500 com o traceback no log do servidor é bom para debug.
        raise # Re-levanta a exceção para FastAPI tratar como 500

    automoveis_resposta = [AutomovelRespostaParaAPI.model_validate(auto_db) for auto_db in resultados_db]
    
    total_paginas = (total_encontrado + paginacao.itens_por_pagina - 1) // paginacao.itens_por_pagina if total_encontrado > 0 else 0

    dados_resposta = MCPDadosResposta(
        automoveis=automoveis_resposta,
        total_encontrado=total_encontrado,
        pagina_atual=paginacao.pagina,
        total_paginas=max(0, total_paginas) # Garante que total_paginas não seja negativo
    )

    return MCPResponse(
        sucesso=True,
        mensagem="Busca realizada com sucesso." if automoveis_resposta or total_encontrado == 0 else "Nenhum automóvel encontrado com os filtros fornecidos na página atual, mas existem resultados em outras páginas.",
        dados=dados_resposta
    )