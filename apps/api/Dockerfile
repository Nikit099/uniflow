FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY apps/api/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY apps/api/app ./app
COPY apps/api/alembic.ini ./
COPY apps/api/alembic ./alembic
COPY apps/api/scripts ./scripts
COPY config /app/config
RUN chmod +x /app/scripts/start.sh && useradd --create-home --uid 10001 app && mkdir -p /data/uploads && chown -R app:app /data
USER app
EXPOSE 8000
CMD ["/app/scripts/start.sh"]
