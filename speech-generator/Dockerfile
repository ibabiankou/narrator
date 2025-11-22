FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install poetry
RUN poetry self add poetry-plugin-export

COPY poetry.lock pyproject.toml ./

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.12-slim AS final

WORKDIR /app

COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./api ./api

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
