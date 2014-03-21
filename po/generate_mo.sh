#!/bin/bash
set -e

OWN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $OWN_DIR

mkdir -p ../mo

for lang in pt; do
    msgfmt -o ../mo/${lang}.mo ${lang}.po
done

