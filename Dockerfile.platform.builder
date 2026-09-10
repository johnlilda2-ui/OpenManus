FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt setup.py ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config
COPY platform_core ./platform_core
COPY alembic.ini ./
COPY alembic ./alembic
COPY main.py run_flow.py run_mcp.py run_mcp_server.py sandbox_main.py setup.py ./

CMD ["python", "-m", "platform_core.app_builder_worker"]
