#!/bin/bash

BASH_XTRACEFD=1
set -x

VERBOSE=0
withzfs="--without zfs"
withldiskfs="--without ldiskfs"

message () {
        [ $VERBOSE -eq 1 ] && echo -e "$@"
        return 0
}

die () {
        echo -e "Error: $@" >&2
        exit 1
}

while getopts vlz FLAG; do
    case "$FLAG" in
      v)
        VERBOSE=1
        ;;
      z)
        withzfs="--with zfs"
        ;;
      l)
        withldiskfs="--with ldiskfs"
        ;;
    esac
done
shift $((OPTIND-1))

sh autogen.sh || die "Lustre autogen failed"
./configure --enable-dist || die "Lustre configure failed"
make srpm || die "Building lustre srpm failed"
rpmbuild --rebuild $withldiskfs $withzfs lustre*.src.rpm || die "rpmbuild failed"
