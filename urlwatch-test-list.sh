#!/bin/bash

webchanges --urls urls-test.yaml --cache cache-test.db --config urlwatch-test.yaml --test-filter 1 $@
