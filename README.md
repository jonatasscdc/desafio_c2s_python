# Desafio Técnico C2S: Agente Virtual de Busca de Automóveis com Python e LLM

## Visão Geral do Projeto

Este projeto foi desenvolvido como parte do desafio técnico para a vaga de Desenvolvedor Python na C2S. O objetivo principal é demonstrar a capacidade de aprendizado de novas tecnologias, domínio de Python e aplicação de boas práticas de engenharia de software na construção de um sistema completo, desde a modelagem de dados até uma interface de usuário conversacional.

A aplicação consiste em um agente virtual de terminal que auxilia usuários a encontrar automóveis com base em seus critérios de busca. O agente utiliza Processamento de Linguagem Natural (PLN), com o auxílio de um Modelo de Linguagem Grande (LLM) via API do Google Gemini, para entender as solicitações do usuário. Os filtros extraídos são enviados a um servidor FastAPI, que por sua vez consulta um banco de dados SQLite populado com dados fictícios de veículos.

## Funcionalidades Principais

*   **Modelagem de Dados Robusta:** Esquema de dados para automóveis com validação utilizando Pydantic.
*   **Banco de Dados:** Uso de SQLAlchemy para ORM e SQLite para persistência. Inclui script para popular o banco com mais de 100 veículos fictícios gerados com a biblioteca Faker.
*   **API Cliente-Servidor (Protocolo MCP):**
    *   Servidor FastAPI expondo um endpoint para busca de automóveis.
    *   Validação de requisições e serialização de respostas com Pydantic.
    *   Documentação automática da API (Swagger UI e ReDoc).
*   **Agente Virtual Conversacional no Terminal:**
    *   Interface de linha de comando interativa.
    *   Utilização de LangChain e Google Gemini API para extração de entidades (filtros de busca) a partir da linguagem natural do usuário.
    *   Coleta interativa de informações e feedback ao usuário sobre os critérios entendidos.
    *   Comunicação com o servidor FastAPI para buscar e apresentar os automóveis correspondentes.
*   **Gerenciamento de Dependências:** Utilização de Poetry para um gerenciamento de dependências moderno e robusto.
*   **Testes Automatizados:** Suíte de testes utilizando Pytest para validar modelos, a API do servidor (com TestClient) e a lógica do agente (com mocks).

## Tecnologias Utilizadas

*   **Linguagem:** Python 3.11+
*   **Gerenciamento de Dependências e Projeto:** Poetry
*   **Servidor API:** FastAPI, Uvicorn
*   **Modelagem e Validação de Dados:** Pydantic (v2)
*   **Banco de Dados e ORM:** SQLite, SQLAlchemy
*   **Geração de Dados Fictícios:** Faker
*   **Processamento de Linguagem Natural (LLM):**
    *   LangChain (para orquestração)
    *   Google Gemini API (modelo `gemini-1.5-flash-latest`)
*   **Cliente HTTP:** Requests (para o agente interagir com a API)
*   **Testes:** Pytest, Pytest-Cov (opcional para cobertura), `unittest.mock`
*   **Variáveis de Ambiente:** `python-dotenv`

## Estrutura do Projeto

```
desafio_c2s_python/
├── .venv/                  # Ambiente virtual gerenciado pelo Poetry (se config. local)
├── data/
│   └── automoveis.db       # Banco de dados SQLite (criado após popular)
├── src/                    # Código fonte da aplicação
│   ├── agent/              # Lógica do agente virtual de terminal
│   │   └── terminal_agent.py
│   ├── core/               # Configurações centrais (ex: banco de dados)
│   │   └── database.py
│   ├── models/             # Modelos Pydantic e SQLAlchemy
│   │   └── automovel_model.py
│   ├── services/           # Lógica de serviços (ex: servidor FastAPI)
│   │   └── mcp_server.py
│   └── scripts/            # Scripts utilitários
│       ├── populate_db.py    # Script para popular o banco
│       └── mcp_client_teste.py # Script simples para testar API (opcional)
├── tests/                  # Testes automatizados
│   ├── agent/
│   ├── models/
│   └── services/
├── .env.example            # Exemplo de arquivo .env (copiar para .env)
├── .gitignore
├── conftest.py             # Configurações do Pytest (ex: PYTHONPATH)
├── main.py                 # Ponto de entrada para o agente de terminal
├── poetry.lock             # Lockfile do Poetry
├── pyproject.toml          # Arquivo de configuração do Poetry (dependências, etc.)
└── README.md               # Este arquivo
```

## Pré-requisitos

Antes de começar, garanta que você tem os seguintes softwares instalados:

1.  **Python:** Versão 3.11 ou superior.
2.  **Poetry:** Para gerenciamento de dependências. Siga as instruções de instalação em [python-poetry.org](https://python-poetry.org/docs/#installation).
3.  **Chave de API do Google Gemini:**
    *   Você precisará de uma chave de API para usar o modelo Gemini Pro.
    *   Obtenha sua chave no [Google AI Studio](https://aistudio.google.com/app/apikey).

## Configuração e Instalação

1.  **Clone o Repositório:**
    ```bash
    git clone https://github.com/jonatasscdc/desafio_c2s_python
    cd desafio_c2s_python
    ```

2.  **Configure as Variáveis de Ambiente:**
    *   Copie o arquivo de exemplo `.env.example` para um novo arquivo chamado `.env` na raiz do projeto:
        ```bash
        cp .env.example .env
        ```
    *   Abra o arquivo `.env` e substitua `SUA_CHAVE_API_AQUI` pela sua chave de API real do Google Gemini:
        ```env
        GOOGLE_API_KEY="SUA_CHAVE_API_AQUI"
        ```
    *   **Importante:** O arquivo `.env` está listado no `.gitignore` para evitar que sua chave de API seja versionada.

3.  **Instale as Dependências:**
    Poetry cuidará da criação do ambiente virtual e da instalação de todas as dependências listadas no `pyproject.toml`.
    ```bash
    poetry install
    ```

## Populando o Banco de Dados

Antes de usar o agente ou a API, é recomendado popular o banco de dados com dados fictícios. Para fazer isso, execute o script de população:

```bash
poetry run python -m src.scripts.populate_db
```
Isso criará o arquivo `data/automoveis.db` (se não existir) e o populará com aproximadamente 100 registros de veículos.

## Executando a Aplicação

A aplicação consiste em duas partes principais que precisam ser executadas: o servidor FastAPI e o agente de terminal.

1.  **Inicie o Servidor FastAPI:**
    Abra um terminal na raiz do projeto e execute:
    ```bash
    poetry run uvicorn src.services.mcp_server:app --reload --port 8000
    ```
    *   O servidor estará rodando em `http://127.0.0.1:8000`.
    *   Você pode acessar a documentação interativa da API em:
        *   Swagger UI: `http://127.0.0.1:8000/docs`
        *   ReDoc: `http://127.0.0.1:8000/redoc`
    *   Mantenha este terminal aberto enquanto usa o agente.

2.  **Inicie o Agente de Terminal:**
    Abra **outro** terminal na raiz do projeto e execute:
    ```bash
    poetry run python main.py
    ```
    O agente irá saudá-lo e você poderá começar a interagir para buscar carros.

    **Exemplos de Interação:**
    *   `Você: quero um fiat uno vermelho`
    *   `Você: procuro um jeep compass 2021 a partir de 100 mil`
    *   `Você: tem volkswagen T-Cross flex até 120000?`
    *   `Você: buscar` (após fornecer alguns critérios)
    *   `Você: sair` (para encerrar a conversa)

## Executando os Testes

Para rodar a suíte de testes automatizados (usando Pytest):

```bash
poetry run pytest -v```
Para incluir um relatório de cobertura de testes (requer `pytest-cov`):
```bash
poetry run pytest --cov=src -v
```

## Demonstração da "Bagagem Sênior"

Este projeto busca demonstrar experiência e maturidade em desenvolvimento através de:

*   **Gerenciamento de Projeto:** Uso de Poetry para um fluxo de trabalho de dependências e empacotamento moderno e reprodutível.
*   **Arquitetura e Design:**
    *   Separação clara de responsabilidades (Modelos, Lógica de Banco, Serviços/API, Agente, Scripts).
    *   Design de API RESTful com FastAPI, seguindo boas práticas (versionamento de endpoint, contratos claros com Pydantic).
    *   Fluxo de dados bem definido: Agente -> API -> Banco.
*   **Qualidade de Código:**
    *   Utilização de tipagem estática (type hints) para maior clareza e detecção precoce de erros.
    *   Código modular e organizado em funções e classes com propósito definido.
    *   Validação de dados robusta em múltiplas camadas (Pydantic nos modelos e na API).
*   **Tecnologias e Ferramentas:**
    *   Seleção de bibliotecas padrão e bem estabelecidas no ecossistema Python (SQLAlchemy, Pydantic, FastAPI, Requests, Faker).
    *   Integração de uma tecnologia mais recente e complexa (LLM com LangChain e Google Gemini API) para uma tarefa de PLN.
*   **Testabilidade:**
    *   Criação de testes unitários e de integração para diferentes componentes.
    *   Uso de um banco de dados em memória para testes de serviço isolados e rápidos.
    *   Utilização de mocking para testar unidades que dependem de serviços externos (LLM, API HTTP).
*   **Documentação:** Um `README.md` detalhado para facilitar a compreensão e execução do projeto.
*   **Resolução de Problemas:** Demonstração implícita através da entrega de um projeto funcional e testado.

## Possíveis Melhorias e Próximos Passos

*   **NLU e Diálogo do Agente:**
    *   Refinar ainda mais os prompts do LLM para melhor extração e tratamento de ambiguidades.
    *   Utilizar o campo `outras_caracteristicas` extraído pelo LLM para filtrar por cor, opcionais, etc.
    *   Implementar um gerenciamento de estado da conversa mais sofisticado para permitir diálogos mais longos e complexos (ex: refinar busca, corrigir filtros anteriores de forma mais natural).
    *   Usar o LLM para gerar respostas mais dinâmicas e contextuais do agente.
*   **Servidor API:**
    *   Adicionar mais filtros de busca (ex: quilometragem, número de portas, cor, transmissão).
    *   Implementar autenticação se a API fosse exposta publicamente.
    *   Melhorar o tratamento de erros e logging.
*   **Testes:** Aumentar a cobertura de testes, especialmente para cenários mais complexos do agente e da API.
*   **Interface:** Evoluir para uma interface web ou um bot em plataformas de mensagem.

## Autor

Jonatas Sampaio Carvalho De Carlos
[[https://linkedin.com/in/jonatasscdc]] 
[[https://github.com/jonatasscdc]]

---

Obrigado pela oportunidade de realizar este desafio!
