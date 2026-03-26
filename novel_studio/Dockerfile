FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY novel_app /app/novel_app
COPY scripts /app/scripts
COPY langgraph.json /app/langgraph.json

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "novel_app.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
