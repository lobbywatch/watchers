#!/bin/bash

tmpfile=$(mktemp /tmp/names.XXXXXX)

if [[ -z "$NO_REPLACE" ]]; then
	tee $tmpfile \
		| sed -E ":a;\$!{N;ba}; s/($(cat parliamentarians.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(:?\2)?\\s+\3/' | paste -sd'|'))/🙋\1🙋/gi" \
		| sed -E ":a;\$!{N;ba}; s/($(cat parliamentarians.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s+\1(:?\2)?/' | paste -sd'|'))/🙋\1🙋/gi" \
		| sed -E ":a;\$!{N;ba}; s/($(cat lobbyists.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(:?\2)?\\s+\3/' | paste -sd'|'))/👻\1👻/gi" \
		| sed -E ":a;\$!{N;ba}; s/($(cat lobbyists.csv | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s+\1(:?\2)?/' | paste -sd'|'))/👻\1👻/gi" \
		| grep -zPo "(?s)([\x{1F47B}\x{1F64B}]).*?\1" \
		| sed -E ":a;\$!{N;ba}; s/[[:blank:]\n\r]+/ /gi" \
		| tr '\0' '\n'
else
	tee $tmpfile
fi

rm $tmpfile