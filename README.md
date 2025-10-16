# Lobbywatch Resources

## Prototype Based on `urlwatch`

`urlwatch` is a command-line utility which allows checking for changes to web pages. The state (from previous runs) is by default persisted in a SQLite database (Redis being the other alternative).

For Lobbywatch the idea is to run the tool periodically (e.g. once per day) and notify the team using a dedicated Slack channel.

As an additional benefit the Slack notifications should also highlight the names matching persons (and parlamentarians) in the Lobbywatch database.

### Usage

1. Research the page to add and figure out what CSS selector to apply
2. Add the page definition to `urls-test.yaml` and test the output using `./urlwatch-test.sh`
3. Once satisfied transfer the page to `urls.yaml` and run `./urlwatch-import.sh <n>` where `<n>` is the job number
4. Finally run `./urlwatch.sh` which will send a Slack notification

Periodically the name list for the name matching should also be updated. This can be done using the `load-personen.sh` script.

## Containerized setup

### Build

Container images is currently built locally.

```shell
# add connection for pushing images between hosts without a registry in-between
podman system connection add infomaniak-vm ssh://almalinux@84.xxx.xx.xx

podman build -t lobbywatch/website-updates .
podman image scp lobbywatch/website-updates:latest infomaniak-vm::
```

### Run

```shell
# create secrets
cat deploy-key-website-bot | podman secret create website-updates-repo-ssh-key -
cat .env | podman secret create website-updates-env-file -

# run container
podman run --rm --secret website-updates-repo-ssh-key,target=/home/bot/.ssh/id_ed25519 --secret website-updates-env-file,target=/opt/website-updates/.env lobbywatch/website-updates
```
