FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies needed for pymupdf and reportlab
RUN apt-get update && apt-get install -y \
    build-essential \
    libfreetype6-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Expose port 8000
EXPOSE 8000

# Run gunicorn with 600s timeout
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "--workers", "2", "core.wsgi:application"]
