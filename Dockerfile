FROM python:3.11-slim

WORKDIR /app
COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api/src /app/src
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "aegisforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
