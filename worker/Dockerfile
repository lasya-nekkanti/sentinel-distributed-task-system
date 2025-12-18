FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code + worker code
COPY common /app/common
COPY worker /app

# Make /app discoverable for Python imports
ENV PYTHONPATH=/app

CMD ["python", "worker.py"]

