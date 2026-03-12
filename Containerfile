FROM python:3.14.2-slim-bookworm@sha256:e8a1ad81a9fef9dc56372fb49b50818cac71f5fae238b21d7738d73ccae8f803

RUN apt-get update && apt-get install -y pkg-config gcc libmariadb-dev-compat

RUN pip install poetry

WORKDIR /opt/hr-watcher

# TODO build from git repo, not local source
ADD . . 

RUN poetry install --no-root

ENTRYPOINT ["poetry", "run", "python", "shab-download.py", "--json", "slack"]

