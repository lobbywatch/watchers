# Website watcher notification filter

Receives webhooks from our [changedetection.io](https://changedetection.io) instance and passes them on to kChat if
the change contains a name we care about.

## Develop

```sh
cp config.toml.example config.toml
poetry install --no-root
poetry run fastapi dev
curl -X POST -d '{"watch_url":"https://test.ch","diff":"hans peter","diff_url":"https://some.com","huh":1}' -H 'content-type: application/json' -H 'X-Access-Token: verysecret' http://localhost:8000/change
```

## Run in production

See [infrastructure repo](https://github.com/lobbywatch/infrastructure)
