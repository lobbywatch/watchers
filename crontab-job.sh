#!/bin/bash

PYTHONIOENCODING="UTF-8"
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
(
	umask 022 \
	&& cd ${SCRIPT_DIR} \
	&& git pull -f \
	&& ./load-persons.sh \
	&& ./urlwatch.sh \
	&& git add . \
	&& (git commit -m "execution from $(date)" && git push || true) \
) >> ${HOME}/urlwatch.log 2>&1
