#!/bin/bash

webchanges --urls urls.yaml --cache cache.db --config urlwatch-import.yaml --hooks hooks.py $@
