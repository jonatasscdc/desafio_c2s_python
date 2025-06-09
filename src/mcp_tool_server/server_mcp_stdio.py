# src/mcp_tool_server/server_mcp_stdio.py
import asyncio
import sys
import traceback
from typing import Optional
from mcp.server.fastmcp import FastMCP

from .tool_definitions import FiltrosBuscaCarroToolInput, BuscaCarroToolOutput
from .tool_logic import executar_busca_de_carros_no_banco

# Inicializar o servidor MCP.
mcp_server = FastMCP(
    "ServidorDeBuscaDeCarros",
    description="Um servidor MCP que fornece uma ferramenta para buscar informações sobre automóveis."
)

# Definir a ferramenta usando o decorador do SDK MCP
@mcp_server.tool(
    name="buscar_carros_detalhados",
    description="Busca carros no banco de dados com base em filtros detalhados como marca, modelo, ano, tipo de combustível e faixa de preço. Retorna uma lista de carros e informações de paginação.",
)
async def buscar_carros_tool_mcp(
    marca: Optional[str] = None,
    modelo: Optional[str] = None,
    ano_min: Optional[int] = None,
    ano_max: Optional[int] = None,
    tipo_combustivel: Optional[str] = None,
    preco_min: Optional[float] = None,
    preco_max: Optional[float] = None,
    pagina: int = 1,
    itens_por_pagina: int = 5
) -> BuscaCarroToolOutput:
    """Ponto de entrada da ferramenta MCP para buscar carros."""
    
    # Reconstruct the filtros object from individual parameters
    filtros = FiltrosBuscaCarroToolInput(
        marca=marca,
        modelo=modelo,
        ano_min=ano_min,
        ano_max=ano_max,
        tipo_combustivel=tipo_combustivel,
        preco_min=preco_min,
        preco_max=preco_max,
        pagina=pagina,
        itens_por_pagina=itens_por_pagina
    )
    
    print(f"[Servidor MCP - STDIO] Ferramenta 'buscar_carros_detalhados' chamada com input: {filtros.model_dump_json(indent=2)}", file=sys.stderr)
    
    loop = asyncio.get_event_loop()
    try:
        resultado = await loop.run_in_executor(None, executar_busca_de_carros_no_banco, filtros)
        print(f"[Servidor MCP - STDIO] Ferramenta retornando resultado...", file=sys.stderr)
        return resultado
    except Exception as e:
        print(f"[Servidor MCP - STDIO] Erro na execução da ferramenta: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return BuscaCarroToolOutput(
            automoveis_encontrados=[], total_geral_encontrado=0,
            pagina_atual=filtros.pagina, itens_por_pagina=filtros.itens_por_pagina,
            total_paginas=0, mensagem=f"Erro interno ao processar a busca: {str(e)}"
        )

def main():
    """Função principal para iniciar o servidor MCP."""
    print("[Servidor MCP - STDIO] Iniciando servidor de ferramentas MCP...", file=sys.stderr)
    try:
        # A forma correta e simples de iniciar um FastMCP em modo stdio
        mcp_server.run("stdio")
    except Exception as e:
        print(f"[Servidor MCP - STDIO] Erro fatal no servidor: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        print("[Servidor MCP - STDIO] Servidor encerrado.", file=sys.stderr)

if __name__ == "__main__":
    main()