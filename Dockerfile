FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

WORKDIR /app
COPY pyproject.toml README.md ./
COPY repo_alfa ./repo_alfa
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["repo-alfa"]
