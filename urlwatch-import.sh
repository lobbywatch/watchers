#!/bin/bash

if [[ -z "$1" ]]; then
    echo "error: job to be imported must be specified"
    urlwatch --urls urls.yaml --list
    exit 1
fi

NO_REPLACE=1 urlwatch --urls urls.yaml --cache cache.db --config urlwatch-import.yaml $1
