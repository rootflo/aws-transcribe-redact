# Use an official Python 3.11 base image
FROM python:3.11-slim

# Set environment variables
ENV POETRY_VERSION=1.8.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Install Poetry
RUN apt-get update && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
# Update PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy pyproject.toml and poetry.lock if it exists
COPY pyproject.toml poetry.lock* /app/

# Install dependencies (this will also create a virtual environment)
RUN poetry install --no-root

# Copy the rest of the application code
COPY transcribe_parellel.py /app

# Run the Python script
CMD ["poetry", "run", "python", "transcribe_parellel.py"]
