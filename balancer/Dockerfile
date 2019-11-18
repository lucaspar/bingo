FROM bingocrawler/core:latest AS bingocore

# required files
COPY src/poetry.lock src/pyproject.toml /bingo/
COPY src /bingo/bin
COPY .env.aws .env.local /bingo/bin/

# project requirements
WORKDIR /bingo/bin
RUN poetry self:update
RUN poetry config settings.virtualenvs.create false
RUN poetry install --no-interaction

# execute
ENTRYPOINT ["python", "/bingo/bin/domain_balancer.py"]
