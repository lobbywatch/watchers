#!/bin/bash

while IFS="," read -r org_id resource url
do
    mkdir -p "${org_id}"
    monolith --no-audio --no-video --no-fonts --no-metadata --output "${org_id}/${resource}.html" "${url}"
done < <(tail -n +2 resources.csv)
