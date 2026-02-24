FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY app/ app/
COPY data/ data/
COPY .streamlit/ .streamlit/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose Streamlit port
EXPOSE 8501

# Default: run Streamlit Content Hub
CMD ["streamlit", "run", "app/content_hub.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
