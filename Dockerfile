
# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the app
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Railway provides PORT dynamically, so we bind to it
CMD ["sh", "-c", "streamlit run Scripts.py --server.port=$PORT --server.address=0.0.0.0"]
