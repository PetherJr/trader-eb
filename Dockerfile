# Usa imagem oficial do Python 3.11
FROM python:3.11-slim

# Instala git e ferramentas de build (necessárias para iqoptionapi e libs compiladas)
RUN apt-get update && apt-get install -y git build-essential && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia apenas os arquivos necessários primeiro (para aproveitar cache)
COPY requirements.txt /app/

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . /app

# Expõe a porta (Render define via variável de ambiente PORT)
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "app.py"]
