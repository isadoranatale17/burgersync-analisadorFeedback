FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=5000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Garante a existência das pastas de transição e dados
RUN mkdir -p .tmp data

EXPOSE 5000

CMD ["python", "execution/server.py"]
