FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/tmp/hf

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY --chown=10001:10001 download_model.py .

USER 10001

ENTRYPOINT ["python", "download_model.py"]