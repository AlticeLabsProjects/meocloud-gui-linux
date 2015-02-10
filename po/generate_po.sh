#!/bin/bash
find .. -iname "*.py" | xargs xgettext

sed -i 's/CHARSET/UTF-8/g' messages.po

langs=( pt_PT pt_BR )

for lang in "${langs[@]}"; do
    msgmerge -U ${lang}.po messages.po
done

rm *~
