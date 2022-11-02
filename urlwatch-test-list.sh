#!/bin/bash

webchanges --urls urls-test.yaml --cache cache-test.db --config urlwatch-test-list.yaml --hooks hooks.py --test-filter 1 $@
