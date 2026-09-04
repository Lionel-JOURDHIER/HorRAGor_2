FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY provision.py monitors.yml notifications.yml ./

CMD ["uv", "run", "python", "provision.py"]