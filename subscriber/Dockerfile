FROM python:3.12-slim

WORKDIR /app

COPY subscriber/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py /app/config.py
COPY subscriber/subscriber.py /app/subscriber.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "subscriber.py"]
