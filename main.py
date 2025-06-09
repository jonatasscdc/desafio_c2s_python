# main.py
import sys
# Importa a função 'main' que acabamos de corrigir no servidor stdio
from src.mcp_tool_server.server_mcp_stdio import main as server_main

if __name__ == "__main__":
    print("[Servidor MCP Principal] Iniciando servidor de ferramentas MCP...", file=sys.stderr)
    # Carregar variáveis de ambiente do .env para o processo principal
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        # Executa a função 'main' importada do módulo do servidor (agora síncrona)
        server_main()
    except KeyboardInterrupt:
        print("\n[Servidor MCP Principal] Servidor encerrado pelo usuário.", file=sys.stderr)
    finally:
        print("[Servidor MCP Principal] Servidor finalizado.", file=sys.stderr)