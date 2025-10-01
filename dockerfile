# FROM python:3.11-slim

# #Refresh the apt package list, install some build tools (curl, compiler, etc.) without any extras, then clean up the cache so the image is smaller

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     curl build-essential gcc \
#  && rm -rf /var/lib/apt/lists/*

# ENV POETRY_VERSION=2.1.4 \
#     POETRY_VIRTUALENVS_CREATE=false \
#     PIP_DISABLE_PIP_VERSION_CHECK=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1

# RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# WORKDIR /app

# COPY pyproject.toml poetry.lock* ./

# RUN poetry install --no-interaction --no-ansi --no-root

# #Bake a chosen agent
# ARG AGENT_NAME

# COPY agents/${AGENT_NAME} /app/agent

# # Runtime env for web server
# ENV A2A_HOST=0.0.0.0
# ENV A2A_PORT=8000
# EXPOSE 8000

# #Run the agent web service
# CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/agent"]
# dockerfile  (app image)
FROM python:3.11-slim

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

# Install deps first for layer caching
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-ansi --no-root

# copy shared core (centralized modules)
COPY saop/saop_core /app/saop_core

# Bake a chosen agent (from scaffolded output)
ARG AGENT_NAME
COPY agents/${AGENT_NAME} /app/agent

# Make shared code importable
ENV PYTHONPATH=/app

# Runtime env for web server (ports can be overridden by Compose)
ENV A2A_HOST=0.0.0.0
ENV A2A_PORT=8000
EXPOSE 8000

# Run the agent web service from /app/agent
CMD ["poetry", "run", "uvicorn", "main:app","--host", "0.0.0.0","--port", "8000","--app-dir", "/app/agent"]
