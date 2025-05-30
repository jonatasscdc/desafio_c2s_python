import uuid
from datetime import datetime 
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Usar Enums para campos com valores predefinidos 
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
    marca: str = Field(..., min_length=1, max_length=50, description="Marca do veículo")
    modelo: str = Field(..., min_length=1, max_length=50, descripttion="Modelo do veículo")
    ano_fabricacao: int = Field(..., gt=1900, lt=datetime.now().year + 2, description="Ano de fabricação do veículo")
    ano_modelo: int = Field(..., gt=1900, lt=datetime.now().year +3, description="Ano do modelo do veículo")
    cor: str = Field(..., min_length=3, max_length=30)
    motorizacao: float = Field(..., gt=0.0, lt=10.0, description="Motorização em litros (ex: 1.0, 2.0)")
    tipo_combustivel: TipoCombustivelEnum = Field(..., description= "Tipo de combustível")
    quilometragem: int = Field(..., ge=0, description="Quilometragem do veículo")
    numero_portas: int = Field(..., ge=2, le=5, description="Número de portas")
    transmissao: TipoTransmissaoEnum = Field(..., description="Tipo de transmissão")
    preco: float = Field(gt=0.0, description="Preço do veículo em R$")
    data_cadastro: datetime = Field(default_factory=datetime.now, description="Data de cadastro do veículo no sistema")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações adicionais sobre o veículo")

# Validador customizado para garantir que ano_modelo >= ano_fabricacao
    @field_validator('ano_modelo')
    def validar_ano_modelo(cls, v, values):
        # O Pydantic V2 mudou a forma como 'values' é acessado em validadores.
        # Precisamos garantir que 'ano_fabricacao' já esteja no dicionário 'values.data'.
        # Se não estiver, o Pydantic ainda não processou esse campo.
        # Para validadores que dependem de outros campos, é mais seguro usar @model_validator (root_validator em V1)
        # Mas para este caso, vamos assumir que 'ano_fabricacao' vem antes ou usar um model_validator se isso falhar.
        # Pydantic V2: 'values' é um FieldValidationInfo
        data = values.data
        if 'ano_fabricacao' in data and v < data['ano_fabricacao']:
            raise ValueError('Ano do modelo deve ser maior ou igual ao ano de fabricação')
        return v

    # Exemplo de configuração para Pydantic (útil para FastAPI)
    class Config:
        populate_by_name = True # Permite usar 'alias' como _id ao invés de id_veiculo
        json_schema_extra = {
            "example": {
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
                "observacoes": "Único dono, todas as revisões feitas."
            }
        }

# Para facilitar a importação, adicione no src/models/__init__.py:
# from .automovel_model import Automovel, TipoCombustivelEnum, TipoTransmissaoEnum

##




