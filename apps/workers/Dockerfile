FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libfftw3-dev \
    libyaml-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install essentia (now works with Python 3.11)
RUN pip install --no-cache-dir essentia

# Copy source code
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app

# Run workers
CMD ["python", "src/main.py"]
