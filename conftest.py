# conftest.py
import sys
import os

# Adiciona a pasta raiz do projeto (que contém 'src') ao sys.path
# para que os testes possam encontrar os módulos em 'src'
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
    # Algumas pessoas preferem adicionar o PROJECT_ROOT e manter os imports como from src.
    # Outras adicionam src diretamente e importam como from models...
    # Para manter seus imports `from src...` intactos, adicionar PROJECT_ROOT é o correto.
    # No entanto, se adicionarmos SRC_PATH, precisaríamos mudar os imports nos testes para from models... etc.

# Para manter seus imports como `from src.models...`, `from src.agent...`,
# precisamos garantir que a pasta ACIMA de `src` (ou seja, a raiz do projeto)
# esteja no path, para que `src` seja um pacote reconhecível.

# Vamos usar a abordagem de adicionar a raiz do projeto.
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT) # Adiciona a pasta raiz do projeto