FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install poetry
RUN poetry self add poetry-plugin-export

COPY speech-generator/poetry.lock speech-generator/pyproject.toml ./speech-generator/

RUN poetry --project=speech-generator export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.12-slim AS final

WORKDIR /app

COPY --from=builder /app/requirements.txt .
COPY speech-generator/log_conf.yaml .
COPY common-lib ./common-lib

RUN pip install --no-cache-dir -r requirements.txt

COPY speech-generator/api ./api

EXPOSE 8001

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8001", "--log-config", "log_conf.yaml"]
