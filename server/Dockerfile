FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY soberana ./soberana
RUN pip install --no-cache-dir ".[postgres,geo]"

EXPOSE 8000
CMD ["uvicorn", "soberana.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
