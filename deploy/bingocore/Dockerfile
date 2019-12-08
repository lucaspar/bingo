FROM python:3.7-alpine as base
FROM base as builder

RUN mkdir /install
WORKDIR /install
FROM base

COPY --from=builder /install /usr/local

# system requirements
RUN apk --no-cache add curl
# RUN apk add --no-cache --update python3-dev build-base libxml2-dev libxslt-dev
RUN apk add --no-cache --update python3-dev build-base libxslt-dev

# libxml install
RUN apk add --no-cache --virtual .build-deps gcc libc-dev libxslt-dev && \
    apk add --no-cache libxslt && \
    pip install --no-cache-dir lxml>=3.5.0 && \
    apk del .build-deps

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
ENV PATH="/root/.local/bin:/root/.poetry/bin:${PATH}"
RUN source $HOME/.poetry/env
