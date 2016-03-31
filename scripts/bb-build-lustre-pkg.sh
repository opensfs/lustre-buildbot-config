#!/bin/bash
set -x

VERBOSE=0
withzfs="--without-zfs"
withldiskfs="--without-ldiskfs"
MAKE_FLAGS=""

message () {
        [ $VERBOSE -eq 1 ] && echo -e "$@"
        return 0
}

die () {
        echo -e "Error: $@" >&2
        exit 1
}

while getopts vlzm: FLAG; do
    case "$FLAG" in
      v)
        VERBOSE=1
        ;;
      z)
        withzfs="--with-zfs"
        ;;
      l)
        withldiskfs="--with-ldiskfs"
        ;;
      m)
        MAKE_FLAGS="$OPTARG"
        ;;
    esac
done
shift $((OPTIND-1))

sh ./autogen.sh || die "Lustre autogen failed"
./configure $withldiskfs $withzfs || die "Lustre configure failed"
make $MAKE_FLAGS -j$(nproc) || die "Building lustre binaries failed"
