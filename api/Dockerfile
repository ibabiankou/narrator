FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install poetry
RUN poetry self add poetry-plugin-export

COPY api/poetry.lock api/pyproject.toml ./api/

RUN poetry --project=api export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.13-slim AS final

WORKDIR /app

COPY --from=builder /app/requirements.txt .
COPY api/log_conf.yaml .
COPY common-lib ./common-lib

RUN pip install --no-cache-dir -r requirements.txt

COPY api/api ./api

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "log_conf.yaml"]
