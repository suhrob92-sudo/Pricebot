FROM python:3.11-slim

WORKDIR /app

# System dependencies for lxml and other C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# --prefer-binary: use pre-built wheels, avoid Rust/C source builds
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .

RUN mkdir -p data

CMD ["python", "-m", "bot.main"]
