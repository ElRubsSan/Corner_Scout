FROM python:3.13-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY analytics ./analytics
COPY backend ./backend
RUN uv sync --locked --no-dev --extra api --extra llm
ENV PATH="/app/.venv/bin:$PATH"
ENV CORNERSCOUT_DATA_DIR=/data
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
