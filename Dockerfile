FROM python:3.11-slim

# Install system dependencies required for downloading and processing files
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    megatools \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone the Telegram Leecher repository
RUN git clone https://github.com/XronTrix10/Telegram-Leecher.git .

# Install Python requirements and force-reinstall Pyrofork/Tgcrypto for channel ID compatibility
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir --force-reinstall pyrofork tgcrypto

# Copy the custom entrypoint script
COPY start.py /app/start.py

# Run the startup script
CMD ["python3", "start.py"]
