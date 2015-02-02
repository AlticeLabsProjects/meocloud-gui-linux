#!/bin/sh

update-desktop-database -q


retry() {
    n=0
    until [ $n -ge 10 ]
    do
        $@ 2> /dev/null && return
        n=$(($n+1))
        sleep 1
    done
    echo
    echo "An error occurred while installing MEO Cloud!" 1>&2
    echo "Please try again, and if it still does not work, please contact the support at #help_url#" 1>&2
    exit 1
}

if command -v curl >/dev/null 2>&1; then
    URL_FETCHER_COMMAND='curl -f'
else
    URL_FETCHER_COMMAND='wget -O-'
fi

if [ -d "/etc/apt/sources.list.d/" ]
then
    # add sapo repository to apt
    retry $URL_FETCHER_COMMAND http://repos.sapo.pt/deb/sapo.list > /etc/apt/sources.list.d/sapo.list
    sed -i 's/stable/##BETA_OR_STABLE##/g' /etc/apt/sources.list.d/sapo.list

    # verify and install sapo repository's GPG key for package verification
    TMPKEY=`mktemp`
    retry $URL_FETCHER_COMMAND http://repos.sapo.pt/deb/gpg-key-sapo-packages > $TMPKEY
    if echo "57241f9d1915a5d27a8e8966b37c0554  $TMPKEY" | md5sum -c --status -
    then
        apt-key add $TMPKEY > /dev/null
        rm $TMPKEY
    else
        echo "ERROR: failed to verify integrity of the repository's GPG key!"
        echo "Please try again, and if it still does not work, please contact the support at #help_url#"
        exit 1
    fi
fi
