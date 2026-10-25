FROM python:3.11-slim

# Install system dependencies required for downloading and processing files
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    megatools \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy your start script and requirements into the container
COPY requirements.txt /app/requirements.txt
COPY start.py /app/start.py

# Install Flask and other root requirements first
RUN pip3 install --no-cache-dir -r requirements.txt

# Clone the Telegram Leecher repository into a separate folder so it doesn't overwrite your files
RUN git clone https://github.com/XronTrix10/Telegram-Leecher.git /app/Telegram-Leecher

# Install bot requirements and force-reinstall Pyrofork/Tgcrypto
RUN pip3 install --no-cache-dir -r /app/Telegram-Leecher/requirements.txt
RUN pip3 install --no-cache-dir --force-reinstall pyrofork tgcrypto

# Run the startup script
CMD ["python3", "start.py"]
