# syntax=docker/dockerfile:1

FROM python:3.14.3-alpine AS builder

RUN apk add --no-cache \
  gcc musl-dev postgresql-dev \
  zlib-dev jpeg-dev freetype-dev libwebp-dev

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

FROM python:3.14.3-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache libpq zlib jpeg freetype libwebp su-exec

COPY --from=builder /install /usr/local

ARG APP_UID=1000
ARG APP_GID=1000
RUN addgroup -g ${APP_GID} app_user \
  && adduser -u ${APP_UID} -G app_user -D app_user \
  && install -d -m 0755 -o app_user -g app_user /app /app/json /app/logs

WORKDIR /app

COPY --chown=app_user:app_user . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "donkeybot.main"]
