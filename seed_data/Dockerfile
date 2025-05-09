FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set execute permissions for the script
RUN chmod +x seed.py

# Default command
CMD ["python", "seed.py"]