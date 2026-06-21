FROM python:3.12-slim

WORKDIR /app

# Install the package (editable not needed in the image).
COPY pyproject.toml ./
COPY alembic.ini ./
COPY backend ./backend
RUN pip install --no-cache-dir .

EXPOSE 8000

# Run migrations, then serve. DATABASE_URL + FERNET_KEY come from the environment.
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
