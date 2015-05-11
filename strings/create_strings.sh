#! /bin/bash
set -e

if [ "$1" == "" ] ; then
    BRAND='meocloud' # default to meocloud
else
    BRAND=$1
fi
BRAND_APP=${BRAND%cloud}
BRAND_APP=$(echo $BRAND_APP | tr '[a-z]' '[A-Z]')
BRAND_APP="$BRAND_APP Cloud"

OWN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $OWN_DIR

echo "Creating gui strings.py for brand $BRAND_APP"

EN_TMP_FILE=$(mktemp)
PT_TMP_FILE=$(mktemp)
BR_TMP_FILE=$(mktemp)
OUT_FILE="../meocloud_gui/strings.py"

python convert_to_native_format.py en.txt $EN_TMP_FILE "$BRAND_APP" > /dev/null
python convert_to_native_format.py pt.txt $PT_TMP_FILE "$BRAND_APP" > /dev/null
python convert_to_native_format.py br.txt $BR_TMP_FILE "$BRAND_APP" > /dev/null

# Clean out file
> $OUT_FILE

echo "# -*- coding: utf-8 -*-" >> $OUT_FILE
echo >> $OUT_FILE
echo "NOTIFICATIONS = {" >> $OUT_FILE
echo "    'en': {" >> $OUT_FILE
cat $EN_TMP_FILE >> $OUT_FILE
echo "    }," >> $OUT_FILE
if [ "$BRAND" == "oicloud" ] ; then
    echo "    'br': {" >> $OUT_FILE
    cat $BR_TMP_FILE >> $OUT_FILE
    echo "    }," >> $OUT_FILE
else
    echo "    'pt': {" >> $OUT_FILE
    cat $PT_TMP_FILE >> $OUT_FILE
    echo "    }," >> $OUT_FILE
fi
echo "}" >> $OUT_FILE

rm $EN_TMP_FILE
rm $PT_TMP_FILE
rm $BR_TMP_FILE
