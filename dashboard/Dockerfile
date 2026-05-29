FROM python:3.12-slim

WORKDIR /app

COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py /app/config.py
COPY dashboard/db.py /app/db.py
COPY dashboard/alarmes.py /app/alarmes.py
COPY dashboard/figuras.py /app/figuras.py
COPY dashboard/app.py /app/app.py

ENV PYTHONUNBUFFERED=1

EXPOSE 8050

CMD ["python", "app.py"]
