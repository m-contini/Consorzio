FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HEADLESS=true
ENV DATA_PATH=/data
# Forza Python a stampare immediatamente ogni riga (unbuffered)
# evitando che i messaggi di log vengano accumulati
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
