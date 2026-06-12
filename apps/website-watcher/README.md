# Website watcher notification filter

Receives webhooks from our [changedetection.io](https://changedetection.io) instance and passes them on to kChat if
the change contains a name we are about.

## Develop

```sh
# create config.toml from config.toml.example
poetry install --no-root
poetry run fastapi dev
curl -X POST -d '{"watch_url":"https://test.ch","diff":"hans peter","diff_url":"https://some.com","huh":1}' -H 'content-type: application/json' -H 'X-Access-Token: verysecret' http://localhost:8000/change
```

## Containerized setup

### Build

Container image is currently built locally.

```shell
# add connection for pushing images between hosts without a registry in-between
podman system connection add infomaniak-apps-vm ssh://debian@analyse.lobbywatch.ch
podman build -t lobbywatch/website-watcher .
# copy image to VM
podman image scp lobbywatch/website-watcher:latest infomaniak-app-vm::
# copy to root registry
podman image scp debian@localhost::lobbywatch/website-watcher root@localhost::
```

### Run

```shell
cat config.toml | podman secret create website-watcher-config -
podman run --rm --secret website-watcher-config,target=/opt/app/config.toml lobbywatch/website-watcher
```

