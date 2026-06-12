# HR (Handelsregister) watcher

## Build

Container image is currently built locally.

```shell
# add connection for pushing images between hosts without a registry in-between
podman system connection add infomaniak-vm ssh://almalinux@84.xxx.xx.xx

podman build -t lobbywatch/hr-watcher .
podman image scp lobbywatch/hr-watcher:latest infomaniak-vm::
```

### Run

```shell
# create secrets
cat .env | podman secret create hr-watcher-env-file -

# run container
podman run --rm --secret hr-watcher-env-file,target=/opt/hr-watcher/.env lobbywatch/hr-watcher
```
