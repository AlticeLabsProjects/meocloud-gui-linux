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

if [ -d "/etc/yum.repos.d/" ]
then
    # add sapo repository to yum
    retry $URL_FETCHER_COMMAND http://repos.sapo.pt/rpm/sapo.repo > /etc/yum.repos.d/sapo.repo
    if [ "##BETA_OR_STABLE##" = "beta" ]; then
        sed -i 's/enabled=0/enabled=1/g' /etc/yum.repos.d/sapo.repo
    fi

    # verify and install sapo repository's GPG key for package verification
    TMPKEY=`mktemp`
    retry $URL_FETCHER_COMMAND http://repos.sapo.pt/rpm/gpg-key-sapo-packages > $TMPKEY
    if echo "4d74575c6d07ba9b72776f421b2d2318  $TMPKEY" | md5sum -c --status -
    then
        rpm --import $TMPKEY
        rm $TMPKEY
    else
        echo "ERROR: failed to verify integrity of the repository's GPG key!"
        echo "Please try again, and if it still does not work, please contact the support at #help_url#"
        exit 1
    fi
fi
