#!/bin/bash

tmpfile=$(mktemp /tmp/names.XXXXXX)

if [[ -z "$NO_REPLACE" ]]; then
	tee $tmpfile \
		| sed -E "s/($(cat personen.csv | sed -E 's/(.*),(.*)/\1[ \\t]+\2/' | paste -sd'|'))/**\1**/g" \
		| sed -E "s/($(cat personen.csv | sed -E 's/(.*),(.*)/\2,[ \\t]+\1/' | paste -sd'|'))/**\1**/g"
else
	tee $tmpfile
fi

rm $tmpfile
