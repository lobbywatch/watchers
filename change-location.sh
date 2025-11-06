#!/bin/sh
poetry run webchanges --config urlwatch.yaml --urls urls.yaml --hooks hooks.py --cache cache.db --change-location "${@}"
