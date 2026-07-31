FROM python:3.11-slim

WORKDIR /app

# Install OS packages for bitsandbytes (if needed). Adjust for your base image.
RUN apt-get update && apt-get install -y git build-essential libsndfile1 wget \
    && rm -rf /var/lib/apt/lists/*

COPY ai/requirements.txt /app/ai/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/ai/requirements.txt

COPY ai /app/ai

CMD ["python", "-u", "ai/deepseek_inference.py", "--test"]
