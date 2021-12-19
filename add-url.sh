#!/bin/bash

export URL=$1
export NAME=$(python -c "import bs4, requests; print(bs4.BeautifulSoup(requests.get('${URL}').content).title.text)")

echo "Adding $NAME: $URL"

envsubst < urls.yaml.tmpl > urls-test.yaml
./urlwatch-test.sh && cat urls-test.yaml >> urls.yaml
