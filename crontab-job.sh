#!/bin/bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
(
	cd ${SCRIPT_DIR} \
	&& git pull -f \
	&& ./urlwatch.sh \
	&& git add . \
	&& (git commit -m "execution from $(date)" && git push || true) \
) >> ${HOME}/urlwatch.log 2>&1
