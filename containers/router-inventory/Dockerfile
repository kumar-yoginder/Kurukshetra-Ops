FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/scripts/monitoring
WORKDIR /app
COPY --from=inventory-source requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /tmp/requirements.txt
COPY --from=inventory-source . /app/scripts/monitoring/router_inventory/
COPY --from=monitoring-entry serve-private-inventory.py /app/scripts/monitoring/serve-private-inventory.py
CMD ["python", "-m", "router_inventory.runtime"]
