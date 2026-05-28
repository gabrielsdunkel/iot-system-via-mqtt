FROM python:3.12-slim

WORKDIR /app

# Instala dependências primeiro (aproveita cache de camada)
COPY publisher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia config.py compartilhado e o código do publisher
COPY config.py /app/config.py
COPY publisher/simulador.py /app/simulador.py
COPY publisher/publisher.py /app/publisher.py

# Logs Python sem buffer (importante para ver output em tempo real no docker logs)
ENV PYTHONUNBUFFERED=1

CMD ["python", "publisher.py"]
