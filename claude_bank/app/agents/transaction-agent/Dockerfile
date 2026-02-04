FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
COPY ../common /app/common
COPY ../a2a-sdk /app/a2a_sdk
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
EXPOSE 8101
HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import httpx; httpx.get('http://localhost:8101/health').raise_for_status()" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8101"]
