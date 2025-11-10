# --- 1. The "Builder" Stage ---
# This stage builds the dependencies using Poetry
FROM python:3.13-slim AS builder

# Set the working directory
WORKDIR /app

# Install poetry
# We use pip to keep the layer clean
RUN pip install poetry

# Copy *only* the dependency files to leverage caching
COPY poetry.lock pyproject.toml ./

RUN poetry self add poetry-plugin-export

# Export dependencies to a standard requirements.txt
# --without-hashes is recommended for Docker builds
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# --- 2. The "Final" Stage ---
# This stage builds the minimal production image
FROM python:3.13-slim AS final

WORKDIR /app

# Create a non-privileged user to run the app
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy the requirements.txt from the builder stage
COPY --from=builder /app/requirements.txt .

# Install the runtime dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
# This is done *after* pip install to leverage layer caching
COPY ./api ./api

# Change ownership of the app directory to the new user
RUN #chown -R api:appgroup /app

# Switch to the non-root user
#USER appuser

# Expose the port the app will run on
EXPOSE 8000

# Run the Uvicorn server
# "app.main:app" means: In the "app/main.py" file, find the object named "app"
# "--host 0.0.0.0" is essential to accept connections inside Docker
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
