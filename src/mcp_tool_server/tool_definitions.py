# src/mcp_tool_server/tool_definitions.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

# <<<<<<<<<<<<<<<<<<<< CORREÇÃO DA IMPORTAÇÃO AQUI >>>>>>>>>>>>>>>>>>>>
# DE: from src.models.automovel_model import TipoCombustivelEnum
# PARA:
from ..models.automovel_model import TipoCombustivelEnum

class FiltrosBuscaCarroToolInput(BaseModel):
    """Esquema de input para a ferramenta de busca de carros via MCP."""
    model_config = ConfigDict(extra='forbid')

    marca: Optional[str] = Field(default=None, description="Marca do veículo. Ex: Fiat")
    modelo: Optional[str] = Field(default=None, description="Modelo do veículo. Ex: Uno")
    ano_min: Optional[int] = Field(default=None, description="Ano mínimo de fabricação.")
    ano_max: Optional[int] = Field(default=None, description="Ano máximo de fabricação.")
    tipo_combustivel: Optional[str] = Field(default=None, description=f"Tipo de combustível. Um de: {', '.join([e.value for e in TipoCombustivelEnum])}")
    preco_min: Optional[float] = Field(default=None, description="Preço mínimo desejado.")
    preco_max: Optional[float] = Field(default=None, description="Preço máximo desejado.")
    pagina: int = Field(default=1, gt=0, description="Número da página de resultados.")
    itens_por_pagina: int = Field(default=5, gt=0, le=20, description="Número de itens por página.")

class AutomovelToolOutput(BaseModel):
    """Esquema de um único automóvel retornado pela ferramenta."""
    model_config = ConfigDict(from_attributes=True)

    marca: str
    modelo: str
    ano_fabricacao: int
    ano_modelo: int
    cor: str
    motorizacao: float
    tipo_combustivel: str
    quilometragem: int
    numero_portas: int
    transmissao: str
    preco: float

class BuscaCarroToolOutput(BaseModel):
    """Esquema de output da ferramenta de busca de carros via MCP."""
    automoveis_encontrados: List[AutomovelToolOutput]
    total_geral_encontrado: int
    pagina_atual: int
    itens_por_pagina: int
    total_paginas: int
    mensagem: str