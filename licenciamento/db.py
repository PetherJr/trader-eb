import os
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker

# 🔗 Pega o endereço do banco (vem do Render -> Environment -> DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ Variável de ambiente DATABASE_URL não encontrada!")

# ⚙️ Conexão com o banco
engine = create_engine(DATABASE_URL)

# 🔧 Sessão para executar queries
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🏗️ Base para criar tabelas
Base = declarative_base()


# 📋 Modelo da tabela de licenças
class Licenca(Base):
    __tablename__ = "licencas"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    validade = Column(Date, nullable=False)
    is_trial = Column(Boolean, default=False)


# 📋 Modelo da tabela de planos
class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)   # Mensal, Trimestral, Anual
    dias = Column(Integer, nullable=False)               # Quantos dias de validade
    link_hotmart = Column(String, nullable=False)        # Link de checkout do Hotmart


# 📋 Modelo da tabela de configurações de usuário
class ConfigUsuario(Base):
    __tablename__ = "config_usuarios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)  # ID ou username
    valor_inicial = Column(Integer, default=10)
    stop_win = Column(Integer, default=0)
    stop_loss = Column(Integer, default=0)
    martingale = Column(Boolean, default=False)
    soros = Column(Boolean, default=False)
    payout_minimo = Column(Integer, default=70)
    
class Estrategia(Base):
    __tablename__ = "estrategias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    descricao = Column(String, nullable=True)
    ativa = Column(Boolean, default=True)

class Taxa(Base):
    __tablename__ = "taxas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    valor = Column(String, nullable=False)  # ex.: "80%" ou "1.5"

class Sinal(Base):
    __tablename__ = "sinais"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, nullable=False)  # username ou ID do Telegram
    par = Column(String, nullable=False)      # ex.: EUR/USD
    horario = Column(String, nullable=False)  # ex.: 13:05
    direcao = Column(String, nullable=False)  # CALL ou PUT
    expiracao = Column(String, nullable=True) # ex.: 5m
    ativo = Column(Boolean, default=True)
    
class Resultado(Base):
    __tablename__ = "resultados"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, nullable=False)   # chat_id numérico do Telegram
    par = Column(String, nullable=False)       # ex.: EUR/USD
    horario = Column(String, nullable=False)   # ex.: 11:37
    direcao = Column(String, nullable=False)   # CALL ou PUT
    expiracao = Column(String, nullable=True)  # ex.: 5m
    status = Column(String, default="executado")  # depois pode ser "vitória", "derrota"

class CredencialCorretora(Base):
    __tablename__ = "credenciais_corretoras"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, unique=True, nullable=False)  # chat_id numérico
    corretora = Column(String, nullable=False, default="iqoption")
    email = Column(String, nullable=False)
    senha = Column(String, nullable=False)
    conta_demo = Column(Boolean, default=True)  # True = demo, False = real





# 🚀 Função para criar as tabelas no banco (caso não existam ainda)
def init_db():
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        # Garante coluna extra na tabela de licenças
        conn.execute(
            text("ALTER TABLE licencas ADD COLUMN IF NOT EXISTS is_trial BOOLEAN DEFAULT FALSE;")
        )
        # Só cria a tabela se não existir (sem travar se já existe)
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS credenciais_corretoras (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR UNIQUE NOT NULL,
                corretora VARCHAR NOT NULL DEFAULT 'iqoption',
                email VARCHAR NOT NULL,
                senha VARCHAR NOT NULL,
                conta_demo BOOLEAN DEFAULT TRUE
            )
            """)
        )
        conn.commit()


