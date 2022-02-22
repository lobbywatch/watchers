#!/bin/bash
if grep "$1" urls.yaml > /dev/null; then
    echo "URL already added: $1" && exit 0
fi

export PYTHONIOENCODING=utf-8
export URL=$1
export NAME=$(python -c "import bs4, requests; print(bs4.BeautifulSoup(requests.get('${URL}').content).title.text)" | sed 's/^ *//; s/ *$//; /^$/d')

echo "Adding $NAME: $URL"

envsubst < urls.yaml.tmpl > urls-test.yaml
./urlwatch-test.sh && cat urls-test.yaml >> urls.yaml
