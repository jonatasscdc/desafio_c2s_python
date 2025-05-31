# main.py
from src.agent import terminal_agent

if __name__ == "__main__":
    # Antes de rodar, certifique-se de que o servidor FastAPI (mcp_server.py)
    # esteja rodando em outro terminal:
    # poetry run uvicorn src.services.mcp_server:app --reload

    terminal_agent.iniciar_conversa()