FROM python:3.13.1-alpine3.21

# Disable byte code storing - it will be compiled on fly and put into RAM by container
ENV PYTHONDONTWRITEBYTECODE=1
# Logs will be written to console immediately
ENV PYTHONUNBUFFERED=1

RUN adduser -D -u 1000 appuser

WORKDIR /app

RUN mkdir -p /app/media /app/logs && \
    chown -R appuser:appuser /app/media /app/logs

USER appuser

# Adding dir where pip, ran from appuser, puts binaries into PATH variable
ENV PATH="/home/appuser/.local/bin:$PATH"

RUN --mount=type=bind,source=requirements.txt,target=/app/requirements.txt pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser manage.py /app
COPY --chown=appuser:appuser bingX/ /app/bingX/
COPY --chown=appuser:appuser trading_buddy_backend/ /app/trading_buddy_backend
COPY --chown=appuser:appuser trading_buddy/ /app/trading_buddy


EXPOSE 8000

# Run migrations and start Gunicorn using UV
CMD ["sh", "-c", "python manage.py migrate && gunicorn trading_buddy_backend.wsgi:application --bind 0.0.0.0:8000 --workers 1"]


