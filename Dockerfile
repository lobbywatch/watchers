FROM python:3.13.7-slim-bookworm@sha256:adafcc17694d715c905b4c7bebd96907a1fd5cf183395f0ebc4d3428bd22d92d

RUN apt-get update && apt-get install -y ssh git jq mariadb-client libxml2-dev libxslt-dev bash pipx nano && apt-get clean

RUN useradd -u 1000 --create-home --shell /usr/bin/bash bot

ENV PATH=/home/bot/.local/bin:$PATH

USER bot

# from https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
RUN mkdir /home/bot/.ssh && echo 'github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl' > /home/bot/.ssh/known_hosts

RUN pipx install poetry

WORKDIR /opt/website-watcher

# TODO build from git repo, not local source
ADD --chown=1000 . . 

RUN poetry install --no-root

ENTRYPOINT ["/opt/website-watcher/run.sh"]
