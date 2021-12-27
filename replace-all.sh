#!/bin/bash

tmpfile=$(mktemp /tmp/names.XXXXXX)
tmpfile2=$(mktemp /tmp/names2.XXXXXX)

if [[ -z "$NO_REPLACE" ]]; then
	parl=$(awk 'BEGIN{FS=OFS=","} { print $1, gensub(/([^- ]+)[- ]([^- ]+)/, "\\1([- ]\\2)?", "g", $2) }' parliamentarians.csv | sed 's/Delphine/Délphine/g; s/Bellaiche/Bellaïche/g; s/é/[eé]/g; s/è/[eè]/g; s/à/[aà]/g; s/ç/[cç]/g; s/ë/[eë]/g; s/ï/[iï]/g; s/ò/[oò]/g')
	parl_fl=$(echo "$parl" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(:?\2)?\\s*\3/' | paste -sd'|' | sed 's/(:?)?//g')
	parl_lf=$(echo "$parl" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s*\1(:?\2)?/' | paste -sd'|' | sed 's/(:?)?//g')

	lobby=$(awk 'BEGIN{FS=OFS=","} { print $1, gensub(/([^- ]+)[- ]([^- ]+)/, "\\1([- ]\\2)?", "g", $2) }' lobbyists.csv | sed 's/é/[eé]/g; s/è/[eè]/g; s/à/[aà]/g; s/ç/[cç]/g; s/ë/[eë]/g; s/ï/[iï]/g; s/ò/[oò]/g')
	lobby_fl=$(echo "$lobby" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\1(:?\2)?\\s*\3/' | paste -sd'|' | sed 's/(:?)?//g')
	lobby_lf=$(echo "$lobby" | sed -E 's/([^ ,]+)([^,]+)?,(.+)/\3,?\\s*\1(:?\2)?/' | paste -sd'|' | sed 's/(:?)?//g')
	tee $tmpfile \
		| sed $'s/\xC2\xA0/ /g' \
		| (rg -i --pcre2 "($parl_fl|$parl_lf)" --replace '🙋${1}🙋' --color never --null-data - || cat $tmpfile) \
		| tee $tmpfile2 \
		| (rg -i --pcre2 "($lobby_fl|$lobby_lf)" --replace '👻${1}👻' --color never --null-data - || cat $tmpfile2) \
		| grep -zPo "(?s)([\x{1F47B}\x{1F64B}]).*?\1" \
		| sed -E ":a;\$!{N;ba}; s/[[:blank:]\n\r]+/ /gi" \
		| tr '\0' '\n'

		# to skip duplicates:
		# | awk '!x[$0]++'
else
	tee $tmpfile
fi

rm $tmpfile && rm $tmpfile2