FROM python:3.7-alpine as base
FROM base as builder

RUN mkdir /install
WORKDIR /install
FROM base

# required files
COPY --from=builder /install /usr/local
COPY .env poetry.lock pyproject.toml /bingo/
COPY src /bingo/bin

# system requirements
RUN apk --no-cache add curl
RUN apk add --no-cache --update python3-dev gcc build-base libxml2-dev libxslt-dev

# project requirements
WORKDIR /bingo/bin
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
ENV PATH="/root/.local/bin:/root/.poetry/bin:${PATH}"
RUN source $HOME/.poetry/env
RUN poetry self:update
RUN poetry config settings.virtualenvs.create false
RUN poetry install --no-interaction

# execute
CMD ["python", "/bingo/bin/domain_balancer.py"]
