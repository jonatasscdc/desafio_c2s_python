# src/models/automovel_model.py
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator, ValidationInfo

# Usar Enums para campos com valores predefinidos é uma boa prática
class TipoCombustivelEnum(str, Enum):
    GASOLINA = "Gasolina"
    ETANOL = "Etanol"
    FLEX = "Flex"
    DIESEL = "Diesel"
    ELETRICO = "Elétrico"
    HIBRIDO = "Híbrido"

class TipoTransmissaoEnum(str, Enum):
    MANUAL = "Manual"
    AUTOMATICO = "Automático"
    AUTOMATIZADO = "Automatizado" # Ex: Dualogic, I-Motion
    CVT = "CVT"

class Automovel(BaseModel):
    id_veiculo: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    marca: str = Field(..., min_length=2, max_length=50, description="Marca do veículo")
    modelo: str = Field(..., min_length=1, max_length=50, description="Modelo do veículo")
    ano_fabricacao: int = Field(..., gt=1900, lt=datetime.now().year + 2, description="Ano de fabricação do veículo")
    ano_modelo: int = Field(..., gt=1900, lt=datetime.now().year + 3, description="Ano do modelo do veículo")
    cor: str = Field(..., min_length=3, max_length=30)
    motorizacao: float = Field(..., gt=0.0, lt=10.0, description="Motorização em litros (ex: 1.0, 2.0)")
    tipo_combustivel: TipoCombustivelEnum = Field(..., description="Tipo de combustível")
    quilometragem: int = Field(..., ge=0, description="Quilometragem do veículo") # ge = greater than or equal
    numero_portas: int = Field(..., ge=2, le=5, description="Número de portas") # le = less than or equal
    transmissao: TipoTransmissaoEnum = Field(..., description="Tipo de transmissão")
    preco: float = Field(..., gt=0.0, description="Preço do veículo em R$")
    data_cadastro: datetime = Field(default_factory=datetime.now, description="Data de cadastro do veículo no sistema")
    # Atributo opcional
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações adicionais sobre o veículo")

    # Validador customizado para garantir que ano_modelo >= ano_fabricacao
    @field_validator('ano_modelo')
    @classmethod # Adicionar @classmethod se for um método de classe, ou remover se for método de instância (Pydantic V2 prefere sem para field_validator simples)
                 # Para field_validator, o @classmethod não é estritamente necessário em Pydantic v2, mas não prejudica.
                 # Pydantic V2 passa ValidationInfo que contém 'data'.
    def validar_ano_modelo(cls, v: int, info: ValidationInfo) -> int: # v é o valor do campo, info contém outros campos
        # Em Pydantic v2, 'info.data' contém o dicionário de campos já validados.
        if 'ano_fabricacao' in info.data and info.data['ano_fabricacao'] is not None and v < info.data['ano_fabricacao']:
            raise ValueError('Ano do modelo deve ser maior ou igual ao ano de fabricação')
        return v

    # Exemplo de configuração para Pydantic (útil para FastAPI)
    class Config:
        populate_by_name = True # Permite usar 'alias' como _id ao invés de id_veiculo
        from_attributes = True # <<< ESTA É A LINHA ADICIONADA/CORRIGIDA
        json_schema_extra = {
            "example": {
                "_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", # Exemplo de UUID no alias
                "marca": "Volkswagen",
                "modelo": "Gol",
                "ano_fabricacao": 2020,
                "ano_modelo": 2021,
                "cor": "Branco",
                "motorizacao": 1.0,
                "tipo_combustivel": "Flex",
                "quilometragem": 30000,
                "numero_portas": 4,
                "transmissao": "Manual",
                "preco": 48000.00,
                "data_cadastro": "2024-05-20T10:00:00Z", # Exemplo de datetime
                "observacoes": "Único dono, todas as revisões feitas."
            }
        }

# Para facilitar a importação, adicione no src/models/__init__.py:
# from .automovel_model import Automovel, TipoCombustivelEnum, TipoTransmissaoEnum