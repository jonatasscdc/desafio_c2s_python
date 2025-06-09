# src/mcp_tool_server/tool_logic.py
from sqlalchemy import select, func, and_
from typing import List

# <<<<<<<<<<<<<<<<<<<< CORREÇÃO DAS IMPORTAÇÕES AQUI >>>>>>>>>>>>>>>>>>>>
# DE: from src.core.database import SessionLocal, AutomovelDB
# DE: from src.models.automovel_model import TipoCombustivelEnum as OriginalTipoCombustivelEnum
# DE: from .tool_definitions import FiltrosBuscaCarroToolInput, BuscaCarroToolOutput, AutomovelToolOutput
# PARA:
from ..core.database import SessionLocal, AutomovelDB
from ..models.automovel_model import TipoCombustivelEnum as OriginalTipoCombustivelEnum
from .tool_definitions import FiltrosBuscaCarroToolInput, BuscaCarroToolOutput, AutomovelToolOutput

def executar_busca_de_carros_no_banco(filtros: FiltrosBuscaCarroToolInput) -> BuscaCarroToolOutput:
    db = SessionLocal()
    try:
        query_base = select(AutomovelDB)
        condicoes = []

        if filtros.marca:
            condicoes.append(AutomovelDB.marca.ilike(f"%{filtros.marca}%"))
        if filtros.modelo:
            condicoes.append(AutomovelDB.modelo.ilike(f"%{filtros.modelo}%"))
        if filtros.ano_min:
            condicoes.append(AutomovelDB.ano_fabricacao >= filtros.ano_min)
        if filtros.ano_max:
            condicoes.append(AutomovelDB.ano_fabricacao <= filtros.ano_max)
        
        if filtros.tipo_combustivel:
            try:
                combustivel_enum_valido = OriginalTipoCombustivelEnum(filtros.tipo_combustivel.capitalize())
                condicoes.append(AutomovelDB.tipo_combustivel == combustivel_enum_valido)
            except ValueError:
                print(f"[Lógica Ferramenta] Aviso: Tipo de combustível '{filtros.tipo_combustivel}' inválido fornecido para query, ignorando filtro de combustível.")
        
        if filtros.preco_min:
            condicoes.append(AutomovelDB.preco >= filtros.preco_min)
        if filtros.preco_max:
            condicoes.append(AutomovelDB.preco <= filtros.preco_max)

        if condicoes:
            query_base = query_base.where(and_(*condicoes))

        count_query = select(func.count()).select_from(query_base.order_by(None).alias("subquery_for_count"))
        total_geral = db.scalar(count_query) or 0

        offset = (filtros.pagina - 1) * filtros.itens_por_pagina
        query_final = query_base.order_by(AutomovelDB.marca, AutomovelDB.modelo, AutomovelDB.ano_fabricacao.desc())
        query_final = query_final.offset(offset).limit(filtros.itens_por_pagina)
        
        resultados_db: List[AutomovelDB] = db.execute(query_final).scalars().all()

        automoveis_formatados: List[AutomovelToolOutput] = [
            AutomovelToolOutput.model_validate(auto_db) for auto_db in resultados_db
        ]
        
        total_paginas = (total_geral + filtros.itens_por_pagina - 1) // filtros.itens_por_pagina if total_geral > 0 else 0
        
        mensagem_retorno = f"Encontrados {len(automoveis_formatados)} carros nesta página ({filtros.pagina} de {total_paginas}). Total geral correspondente aos filtros: {total_geral}."
        if not automoveis_formatados and total_geral == 0:
            mensagem_retorno = "Nenhum carro encontrado com os critérios fornecidos."
        elif not automoveis_formatados and total_geral > 0:
            mensagem_retorno = f"Nenhum carro encontrado na página {filtros.pagina}, mas existem {total_geral} resultados em outras páginas."

        return BuscaCarroToolOutput(
            automoveis_encontrados=automoveis_formatados,
            total_geral_encontrado=total_geral,
            pagina_atual=filtros.pagina,
            itens_por_pagina=filtros.itens_por_pagina,
            total_paginas=max(0, total_paginas),
            mensagem=mensagem_retorno
        )
    finally:
        db.close()