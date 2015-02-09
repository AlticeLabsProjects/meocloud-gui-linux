#!/bin/bash
set -e

OWN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $OWN_DIR

mkdir -p ../mo

langs=( pt_PT pt_BR )

for lang in "${langs[@]}"; do
    msgfmt -o ../mo/${lang}.mo ${lang}.po
done

