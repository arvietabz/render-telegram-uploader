FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    megatools \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone repository during build time
RUN git clone https://github.com/XronTrix10/Telegram-Leecher.git /app/Telegram-Leecher

# Install Python requirements during build time
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir -r /app/Telegram-Leecher/requirements.txt

# Install compatible MoviePy and force-reinstall Pyrofork/Tgcrypto
RUN pip3 install --no-cache-dir "moviepy<2.0.0" pyrofork tgcrypto --force-reinstall

# Copy entrypoint script
COPY start.py /app/start.py

CMD ["python3", "start.py"]
