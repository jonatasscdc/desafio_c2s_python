# src/scripts/populate_db.py
import random
from faker import Faker
from sqlalchemy.orm import Session
from src.core.database import SessionLocal, engine, create_db_and_tables, AutomovelDB
from src.models.automovel_model import TipoCombustivelEnum, TipoTransmissaoEnum, Automovel as AutomovelPydantic
from uuid import uuid4
from datetime import datetime, timedelta

# Inicializa o Faker
# Usar 'pt_BR' para dados mais localizados (marcas de carros ainda serão genéricas)
fake = Faker('pt_BR')

# Listas de exemplo para dados mais realistas de carros
MARCAS_COMUNS = ["Fiat", "Volkswagen", "Chevrolet", "Ford", "Hyundai", "Toyota", "Renault", "Honda", "Jeep", "Nissan"]
MODELOS_POR_MARCA = {
    "Fiat": ["Uno", "Mobi", "Argo", "Cronos", "Toro", "Strada", "Pulse"],
    "Volkswagen": ["Gol", "Polo", "Virtus", "Nivus", "T-Cross", "Taos", "Amarok", "Saveiro"],
    "Chevrolet": ["Onix", "Onix Plus", "Tracker", "S10", "Spin", "Montana"],
    "Ford": ["Ka", "Ranger", "Territory", "Bronco"], # Ka saiu de linha, mas pode ter usados
    "Hyundai": ["HB20", "HB20S", "Creta"],
    "Toyota": ["Corolla", "Corolla Cross", "Hilux", "Yaris"],
    "Renault": ["Kwid", "Sandero", "Logan", "Duster", "Oroch"],
    "Honda": ["Fit", "City", "HR-V", "Civic"], # Civic nacional saiu de linha, mas pode ter usados
    "Jeep": ["Renegade", "Compass", "Commander"],
    "Nissan": ["Versa", "Kicks", "Frontier"]
}
CORES_COMUNS = ["Branco", "Preto", "Prata", "Cinza", "Vermelho", "Azul", "Marrom"]

def gerar_automovel_ficticio() -> AutomovelDB:
    """Gera uma instância de AutomovelDB com dados fictícios."""
    marca = random.choice(MARCAS_COMUNS)
    modelo = random.choice(MODELOS_POR_MARCA[marca])
    
    ano_fabricacao = random.randint(2015, datetime.now().year)
    # Ano modelo pode ser o mesmo ou um ano a mais
    ano_modelo = random.choice([ano_fabricacao, ano_fabricacao + 1])
    # Limitar ano_modelo ao próximo ano para não ser muito futurista
    ano_modelo = min(ano_modelo, datetime.now().year + 1)

    # Ajuste para quilometragem ser mais realista com base no ano
    anos_de_uso = datetime.now().year - ano_fabricacao
    quilometragem_anual_media = random.randint(8000, 20000)
    quilometragem = max(0, anos_de_uso * quilometragem_anual_media + random.randint(-5000, 5000))
    if anos_de_uso == 0 : # Carro do ano
        quilometragem = random.randint(0,1000)


    # Motorização mais comum
    motorizacao = random.choice([1.0, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0])
    if marca in ["Jeep", "Ford"] and modelo in ["Ranger", "S10", "Amarok", "Hilux", "Commander", "Frontier"]: # Pickups/SUVs maiores
        motorizacao = random.choice([2.0, 2.5, 2.8, 3.0, 3.2])
    elif marca == "Toyota" and modelo == "Corolla" and ano_fabricacao > 2019: # Híbrido
         motorizacao = 1.8

    # Preço um pouco mais realista com base no ano e marca (muito simplificado)
    preco_base_ano = (ano_fabricacao - 2010) * 3000 + 25000 # Base
    fator_marca = MARCAS_COMUNS.index(marca) * 500 # Marcas "melhores" um pouco mais caras
    preco = preco_base_ano + fator_marca + random.uniform(-5000, 5000)
    preco = round(max(15000, preco), 2) # Preço mínimo de 15k

    # Escolha de combustível e transmissão
    tipo_combustivel = random.choice(list(TipoCombustivelEnum))
    # Carros mais novos tem maior chance de serem Flex no Brasil
    if ano_fabricacao > 2010 and tipo_combustivel not in [TipoCombustivelEnum.DIESEL, TipoCombustivelEnum.ELETRICO, TipoCombustivelEnum.HIBRIDO]:
        tipo_combustivel = TipoCombustivelEnum.FLEX if random.random() > 0.2 else tipo_combustivel
    
    # Se for pickup grande, maior chance de ser Diesel
    if motorizacao > 2.0 and marca in ["Ford", "Chevrolet", "Toyota", "Volkswagen", "Nissan", "Jeep"]:
        if random.random() > 0.4: # 60% de chance de ser Diesel
             tipo_combustivel = TipoCombustivelEnum.DIESEL
    
    if marca == "Toyota" and modelo == "Corolla" and motorizacao == 1.8 and ano_fabricacao > 2019:
        tipo_combustivel = TipoCombustivelEnum.HIBRIDO

    # Lógica simples para elétricos (ainda raros)
    if random.random() < 0.02: # 2% de chance de ser elétrico
        tipo_combustivel = TipoCombustivelEnum.ELETRICO
        motorizacao = random.choice([50, 70, 100, 150]) # Potência em kW para elétricos (apenas para variar)
        preco *= 1.8 # Elétricos são mais caros

    transmissao = random.choice(list(TipoTransmissaoEnum))
    # Carros mais novos e/ou mais caros têm mais chance de ser automáticos/CVT
    if (ano_fabricacao > 2018 or preco > 70000) and transmissao == TipoTransmissaoEnum.MANUAL:
        transmissao = random.choice([TipoTransmissaoEnum.AUTOMATICO, TipoTransmissaoEnum.CVT, TipoTransmissaoEnum.AUTOMATIZADO])


    # Tentativa de criar um objeto Pydantic primeiro para validar os dados gerados
    # Isso é uma boa prática para garantir que os dados fakes estão conforme o esperado
    try:
        automovel_pydantic = AutomovelPydantic(
            # id_veiculo é gerado pelo SQLAlchemy ou pode ser gerado aqui se preferir
            marca=marca,
            modelo=modelo,
            ano_fabricacao=ano_fabricacao,
            ano_modelo=ano_modelo,
            cor=random.choice(CORES_COMUNS),
            motorizacao=round(motorizacao,1),
            tipo_combustivel=tipo_combustivel,
            quilometragem=quilometragem,
            numero_portas=random.choice([2, 4]) if modelo not in ["Toro", "Strada", "Saveiro", "S10", "Amarok", "Hilux", "Ranger", "Montana", "Oroch", "Frontier"] else random.choice([2,4]), # Pickups podem ter 2 ou 4
            transmissao=transmissao,
            preco=preco,
            observacoes=fake.sentence(nb_words=10) if random.random() > 0.5 else None
            # data_cadastro será definida pelo default no modelo SQLAlchemy
        )
        # Converte o modelo Pydantic validado para o modelo SQLAlchemy
        return AutomovelDB(**automovel_pydantic.model_dump(exclude_none=True))

    except Exception as e: # Se a validação Pydantic falhar
        print(f"Erro ao gerar dados fictícios validados: {e}")
        # Poderia tentar novamente ou retornar None e pular este registro
        return None


def popular_banco(db: Session, num_veiculos: int = 100):
    print(f"Iniciando a inserção de {num_veiculos} veículos fictícios...")
    veiculos_inseridos = 0
    for i in range(num_veiculos):
        automovel_db = gerar_automovel_ficticio()
        if automovel_db:
            db.add(automovel_db)
            veiculos_inseridos +=1
            if (i + 1) % 20 == 0: # Commit a cada 20 veículos para não sobrecarregar a sessão
                try:
                    db.commit()
                    print(f"Lote de 20 veículos commitado. Total: {veiculos_inseridos}")
                except Exception as e:
                    db.rollback()
                    print(f"Erro ao commitar lote: {e}. Tentando próximo lote.")
    try:
        db.commit() # Commit final para quaisquer veículos restantes
    except Exception as e:
        db.rollback()
        print(f"Erro no commit final: {e}")
    
    print(f"Concluído! {veiculos_inseridos} veículos inseridos no banco de dados.")


if __name__ == "__main__":
    print("Criando tabelas (se não existirem)...")
    create_db_and_tables() # Garante que a tabela e a pasta 'data' existam
    
    # Obtém uma sessão do banco de dados
    db = SessionLocal()
    try:
        popular_banco(db, num_veiculos=100) # Popula com 100 veículos
    finally:
        db.close() # Fecha a sessão
    print("Script de população finalizado.")