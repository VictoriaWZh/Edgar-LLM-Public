FROM python:3.13-slim

# Set workdir
WORKDIR /app

# Pre-install system deps in one clean layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        cmake \
        build-essential \
        pkg-config \
        python3-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip safely
RUN pip install --no-cache-dir --upgrade pip

# Copy project files after installing deps to optimize caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the rest
COPY . .

# Optional: Default command
CMD ["python"]