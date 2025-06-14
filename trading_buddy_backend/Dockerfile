# Use the official Python runtime image
FROM python:3.13

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y curl

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Create and set the working directory
WORKDIR /app

# Copy only Poetry files first (for caching)
COPY trading_buddy_backend/pyproject.toml trading_buddy_backend/poetry.lock* /app/

# Configure Poetry to not create a virtualenv
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-root

# Copy the full project and bingX library
COPY trading_buddy_backend/ /app/
COPY bingX/ /app/bingX/

# Expose Django's default port
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
