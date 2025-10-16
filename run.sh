#!/usr/bin/bash
set -e

source .env
git pull -f
./load-persons.sh
poetry run webchanges --urls urls.yaml --cache cache.db --config urlwatch.yaml --hooks hooks.py $@
git add .
git commit -m "execution from $(date)"
git push
