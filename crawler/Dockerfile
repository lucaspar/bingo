FROM bingocrawler/core:latest AS bingocore

# lxml requirement
RUN apk add py3-lxml
# RUN pip3 install lxml

# required files for build
COPY src/poetry.lock src/pyproject.toml /bingo/

# project requirements
WORKDIR /bingo/bin
RUN poetry self:update
RUN poetry config settings.virtualenvs.create false
RUN poetry install --no-interaction

# copy source files and env
COPY src /bingo/bin
COPY .env.aws .env.local /bingo/bin/

# execute
ENTRYPOINT ["python", "/bingo/bin/crawler_core.py"]
