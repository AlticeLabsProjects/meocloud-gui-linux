#!/bin/bash
find .. -iname "*.py" | xargs xgettext

sed -i 's/CHARSET/UTF-8/g' messages.po

for lang in pt; do
    msgmerge ${lang}.po messages.po > ${lang}.po
done
