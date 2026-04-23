FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/apps/screener/src

WORKDIR /app

COPY apps/screener /app/apps/screener

WORKDIR /app/apps/screener

CMD ["python", "-m", "screener.main"]
