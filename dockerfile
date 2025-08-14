FROM python:3.11-slim

#Refresh the apt package list, install some build tools (curl, compiler, etc.) without any extras, then clean up the cache so the image is smaller

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-interaction --no-ansi --no-root

#Meant to just copy the text file
COPY test.txt .

EXPOSE 8000

#Intended to allow us to view the container directory in the browser to ensure it's working.
CMD ["python","-m","http.server","8000"]
