import os
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# 🔗 Pega o endereço do banco (vem da variável de ambiente DATABASE_URL no Render)
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


# 🚀 Função para criar as tabelas no banco (caso não existam ainda)
def init_db():
    Base.metadata.create_all(bind=engine)
