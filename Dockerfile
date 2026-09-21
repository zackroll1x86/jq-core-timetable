FROM python:3.12-slim-bookworm AS base

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

RUN apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install --yes --no-install-recommends \
        fonts-noto-cjk \
        libx11-6 \
        libxext6 \
        libxrender1 \
        passwd \
        tk8.6 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY app.py schedule_data.py schedule_pdf.py README.md ./
COPY assets ./assets

FROM base AS test

RUN apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install --yes --no-install-recommends xauth xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY tests ./tests

RUN python -m unittest discover -s tests -v \
    && python -m py_compile app.py schedule_data.py schedule_pdf.py \
    && xvfb-run -a python tests/gui_smoke.py

FROM base AS runtime

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && chown --recursive app:app /app

USER app

ENTRYPOINT ["python", "app.py"]
