#!/bin/bash

tmpfile=$(mktemp /tmp/names.XXXXXX)

if [[ -z "$NO_REPLACE" ]]; then
	tee $tmpfile \
		| sed -E ":a;\$!{N;ba}; s/($(cat parliamentarians.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(\2)?\\s+\3/' | paste -sd'|'))/👩‍🌾\1👩‍🌾/gi" \
		| sed -E ":a;\$!{N;ba}; s/($(cat parliamentarians.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s+\1(\2)?/' | paste -sd'|'))/👩‍🌾\1👩‍🌾/gi" \
		| sed -E ":a;\$!{N;ba}; s/($(cat lobbyists.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(\2)?\\s+\3/' | paste -sd'|'))/👻\1👻/gi" \
		| sed -E ":a;\$!{N;ba}; s/($(cat lobbyists.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s+\1(\2)?/' | paste -sd'|'))/👻\1👻/gi"
else
	tee $tmpfile
fi

rm $tmpfile