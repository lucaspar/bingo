FROM bingocrawler/core:latest AS bingocore

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
ENTRYPOINT ["python", "/bingo/bin/indexer.py"]
