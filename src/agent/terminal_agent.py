# src/agent/terminal_agent.py
import os
import json
import sys
from dotenv import load_dotenv
import asyncio
import anyio
from contextlib import asynccontextmanager
from typing import Optional, List, AsyncGenerator

# LangChain e Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Para ferramentas e agentes LangChain
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import StructuredTool
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field, ConfigDict

# SDK MCP Cliente para STDIO
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Importar os esquemas de input/output da nossa ferramenta MCP
from src.mcp_tool_server.tool_definitions import FiltrosBuscaCarroToolInput, BuscaCarroToolOutput
from src.models.automovel_model import TipoCombustivelEnum as OriginalTipoCombustivelEnum

load_dotenv()

# --- Definição da Ferramenta LangChain que interage com o Servidor MCP via STDIO ---

@asynccontextmanager
async def mcp_tool_client_session() -> AsyncGenerator[ClientSession, None]:
    """Context manager para criar e gerenciar uma sessão de cliente MCP com um subprocesso."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    server_module_path = "src.mcp_tool_server.server_mcp_stdio"
    
    env = os.environ.copy()
    # Adicionar a raiz do projeto ao PYTHONPATH para o subprocesso
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = project_root + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = project_root

    # <<<<<<<<<<<<<<<<<<<< CORREÇÃO FINAL E DEFINITIVA AQUI >>>>>>>>>>>>>>>>>>>>
    # Usar o executável python do ambiente virtual diretamente, com o PYTHONPATH configurado.
    # Isso é mais direto e menos propenso a problemas de aninhamento de `poetry run`.
    server_params = StdioServerParameters(
        command=sys.executable,  # Usa o python.exe do ambiente virtual atual
        args=["-m", server_module_path], # Executa o servidor como um módulo
        env=env, # Passa o ambiente com o PYTHONPATH configurado
        stderr=sys.stderr # Redireciona o erro do servidor para o nosso terminal para debug
    )
    
    command_str = f"{server_params.command} {' '.join(server_params.args)}"
    print(f"\n[Agente MCP Client] Iniciando subprocesso do servidor MCP com comando: {command_str}")
    
    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            print("[Agente MCP Client] Inicializando sessão MCP...")
            await session.initialize()
            print("[Agente MCP Client] Sessão MCP inicializada.")
            yield session

async def invocar_ferramenta_busca_carros_mcp_async(**kwargs) -> str:
    """Invoca a ferramenta 'buscar_carros_detalhados' no servidor MCP."""
    filtros = FiltrosBuscaCarroToolInput.model_validate(kwargs)
    print(f"[Agente MCP Client] Chamando ferramenta 'buscar_carros_detalhados' com input: {filtros.model_dump_json(indent=2)}")

    try:
        async with mcp_tool_client_session() as session:
            tool_result_raw = await session.call_tool("buscar_carros_detalhados", arguments=filtros.model_dump(exclude_none=True))
            print(f"[Agente MCP Client] Resposta crua da ferramenta: {tool_result_raw}")
            
            # Check if the tool call was successful
            if tool_result_raw.isError:
                error_message = "Erro desconhecido"
                if tool_result_raw.content:
                    if isinstance(tool_result_raw.content, list) and len(tool_result_raw.content) > 0:
                        error_message = tool_result_raw.content[0].text if hasattr(tool_result_raw.content[0], 'text') else str(tool_result_raw.content[0])
                    else:
                        error_message = str(tool_result_raw.content)
                print(f"[Agente MCP Client] Erro na ferramenta: {error_message}")
                return f"Desculpe, ocorreu um erro técnico ao tentar buscar os carros: {error_message}"
            
            # Extract the actual content from the successful response
            if not tool_result_raw.content or len(tool_result_raw.content) == 0:
                return "Desculpe, não recebi resposta válida da ferramenta."
            
            # The content should be a JSON string representation of our BuscaCarroToolOutput
            content_text = None
            if hasattr(tool_result_raw.content[0], 'text'):
                content_text = tool_result_raw.content[0].text
            else:
                content_text = str(tool_result_raw.content[0])
            
            try:
                # Parse the JSON content to get our structured result
                import json
                result_data = json.loads(content_text)
                resultado_mcp = BuscaCarroToolOutput.model_validate(result_data)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[Agente MCP Client] Erro ao parsear resposta JSON: {e}")
                print(f"[Agente MCP Client] Conteúdo recebido: {content_text}")
                return f"Desculpe, recebi uma resposta inválida da ferramenta."
            
            if resultado_mcp.automoveis_encontrados:
                output_str = f"{resultado_mcp.mensagem}\nResultados:\n"
                for i, carro in enumerate(resultado_mcp.automoveis_encontrados):
                    output_str += f"{i+1}. {carro.marca} {carro.modelo} ({carro.ano_fabricacao}), Cor: {carro.cor}, Km: {carro.quilometragem}, Preço: R${carro.preco:.2f}\n"
                if resultado_mcp.total_geral_encontrado > len(resultado_mcp.automoveis_encontrados):
                    output_str += f"... e mais {resultado_mcp.total_geral_encontrado - len(resultado_mcp.automoveis_encontrados)} resultados disponíveis."
                return output_str.strip()
            else:
                return resultado_mcp.mensagem
    except Exception as e:
        print(f"❌ Erro crítico ao invocar ferramenta MCP: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f"Desculpe, ocorreu um erro técnico ao tentar buscar os carros."

buscar_carros_tool_langchain = StructuredTool.from_function(
    name="buscar_carros_detalhados_mcp",
    coroutine=invocar_ferramenta_busca_carros_mcp_async,
    description=(
        "Use esta ferramenta para buscar carros no catálogo. "
        "Você DEVE usar esta ferramenta se o usuário fornecer QUALQUER informação de busca (marca, modelo, ano, etc.) ou pedir para buscar. "
        "Forneça à ferramenta todos os filtros que extrair da conversa completa."
    ),
    args_schema=FiltrosBuscaCarroToolInput
)

# --- Configuração do Agente LangChain com Memória ---
def criar_agente_mcp_com_memoria():
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("Chave de API do Google não encontrada no arquivo .env.")

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=google_api_key, temperature=0.0, convert_system_message_to_human=True)
    tools = [buscar_carros_tool_langchain]
    MEMORY_KEY = "chat_history" 

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "Você é um assistente de busca de carros chamado CarFinder. Sua única função é usar a ferramenta 'buscar_carros_detalhados_mcp'.\n"
            "REGRA PRINCIPAL: Assim que o usuário fornecer QUALQUER informação que possa ser um filtro de busca de carro (marca, modelo, ano, tipo de combustível, faixa de preço), ou se ele pedir para 'buscar' ou 'procurar', você DEVE OBRIGATORIAMENTE chamar a ferramenta 'buscar_carros_detalhados_mcp'.\n"
            "Use o `input` do usuário e o `chat_history` para coletar TODOS os argumentos para a ferramenta.\n"
            "NÃO FAÇA PERGUNTAS de acompanhamento se você puder extrair pelo menos UM filtro. Chame a ferramenta imediatamente.\n"
            "Se absolutamente NENHUM filtro for identificável no input e no histórico, responda apenas: 'Por favor, forneça alguns detalhes para a busca (marca, modelo, ano, preço, etc.).'\n"
            "Após a ferramenta retornar, apresente o resultado."
         )),
        MessagesPlaceholder(variable_name=MEMORY_KEY),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    memory = ConversationBufferMemory(memory_key=MEMORY_KEY, return_messages=True)
    agent = create_tool_calling_agent(llm, tools, prompt_template)
    
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, memory=memory, verbose=True, 
        handle_parsing_errors=True, max_iterations=5, return_intermediate_steps=True
    )
    return agent_executor

# --- Lógica da Conversa com o Agente ---
async def iniciar_conversa_mcp_async():
    print("👋 Olá! Sou CarFinder, seu agente de busca de carros (MCP Edition).")
    print("Como posso te ajudar hoje?")
    try:
        agent_executor = criar_agente_mcp_com_memoria()
    except ValueError as e:
        print(f"❌ Erro ao inicializar o agente: {e}")
        return

    while True:
        try:
            entrada_usuario = await anyio.to_thread.run_sync(input, "\nVocê: ")
            if entrada_usuario.lower() in ["sair", "exit", "fim", "tchau", "quit", "parar"]:
                print("Até logo! 👋")
                break
            if not entrada_usuario:
                continue
            
            resposta_agente = await agent_executor.ainvoke({"input": entrada_usuario})
            
            print(f"\n[DEBUG AGENTE] Resposta completa do executor: {json.dumps(resposta_agente, indent=2, default=str)}")
            
            output_do_agente = resposta_agente['output']
            print(f"\nCarFinder: {output_do_agente}")

            if isinstance(resposta_agente.get("intermediate_steps"), list):
                for step_action, step_observation in resposta_agente["intermediate_steps"]:
                    tool_name = getattr(step_action, 'tool', 'N/A')
                    tool_args = getattr(step_action, 'tool_input', getattr(step_action, 'args', 'N/A'))
                    log_message = getattr(step_action, 'log', 'N/A')

                    print(f"  [DEBUG AGENTE INTERMEDIATE STEP]")
                    print(f"    Action/Tool Call: {tool_name}")
                    print(f"    Tool Input: {tool_args}")
                    if hasattr(step_action, 'log') and log_message != 'N/A':
                        print(f"    Log do Agente: {log_message.strip()}")
                    print(f"    Observation (Resultado da Ferramenta): {step_observation}")

        except Exception as e:
            print(f"❌ Desculpe, ocorreu um erro inesperado durante a conversa: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)