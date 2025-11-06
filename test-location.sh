#!/bin/sh
poetry run webchanges --urls urls.yaml --cache cache.db --hooks hooks.py --config urlwatch.yaml --test "${@}"

