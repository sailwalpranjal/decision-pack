FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# The API keeps jobs in memory and writes packs to a temp folder; run as an unprivileged user.
RUN useradd --create-home app
USER app

EXPOSE 8000
CMD ["decisionpack", "serve", "--host", "0.0.0.0", "--port", "8000"]
