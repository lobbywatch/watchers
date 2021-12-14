#!/bin/bash

tmpfile=$(mktemp /tmp/names.XXXXXX)

if [[ -z "$NO_REPLACE" ]]; then
	parl=$(awk 'BEGIN{FS=OFS=","} { print $1, gensub(/([^- ]+)[- ]([^- ]+)/, "\\1([- ]\\2)?", "g", $2) }' parliamentarians.csv | sed 's/Delphine/Délphine/g; s/Bellaiche/Bellaïche/g; s/é/[eé]/g; s/è/[eè]/g; s/à/[aà]/g; s/ï/[iï]/g')
	parl_fl=$(echo "$parl" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(:?\2)?\\s*\3/' | paste -sd'|')
	parl_lf=$(echo "$parl" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s*\1(:?\2)?/' | paste -sd'|')

	lobby=$(awk 'BEGIN{FS=OFS=","} { print $1, gensub(/([^- ]+)[- ]([^- ]+)/, "\\1([- ]\\2)?", "g", $2) }' lobbyists.csv | sed 's/é/[eé]/g; s/è/[eè]/g; s/à/[aà]/g; s/ï/[iï]/g')
	lobby_fl=$(echo "$lobby" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(:?\2)?\\s*\3/' | paste -sd'|')
	lobby_lf=$(echo "$lobby" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s*\1(:?\2)?/' | paste -sd'|')
	tee $tmpfile \
		| sed -E ":a;\$!{N;ba}; s/($parl_fl|$parl_lf)/🙋\1🙋/gi" \
		| sed -E ":a;\$!{N;ba}; s/($lobby_fl|$lobby_lf)/👻\1👻/gi" \
		| grep -zPo "(?s)([\x{1F47B}\x{1F64B}]).*?\1" \
		| sed -E ":a;\$!{N;ba}; s/[[:blank:]\n\r]+/ /gi" \
		| tr '\0' '\n'

		# to skip duplicates:
		# | awk '!x[$0]++'
else
	tee $tmpfile
fi

rm $tmpfile