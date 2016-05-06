#!/bin/bash

# Check for a local cached configuration.
if test -f /etc/buildslave; then
    . /etc/buildslave
else
   echo "Missing configuration /etc/buildslave.  Assuming spl and zfs are"
   echo "already installed and this is a persistent buildslave."
   exit 0
fi

BASH_XTRACEFD=1
set -x

VERBOSE=0
GIT_SPL=https://github.com/zfsonlinux/spl.git
GIT_ZFS=https://github.com/zfsonlinux/zfs.git
BUILD_ROOT=
SPL_TAG="master"
ZFS_TAG="master"

# Utility functions
message () {
    [ $VERBOSE -eq 1 ] && echo -e "$@"
    return 0
}

cleanup () {
    dir -c
    [ -n "${BUILD_ROOT}" ] && rm -Rf ${BUILD_ROOT}
    return 0
}

die () {
    echo -e "Error: $@" >&2
    cleanup
    exit 1
}

install_packages () {
    SUDO="sudo"

    case "$BB_NAME" in
    Amazon*)
        $SUDO rm *.src.rpm *.noarch.rpm 2>&1
        $SUDO yum -y localinstall *.rpm 2>&1
        ;;

    CentOS*)
        $SUDO rm *.src.rpm *.noarch.rpm 2>&1
        $SUDO yum -y localinstall *.rpm 2>&1
        ;;

    Debian*)
        for file in *.deb; do
            $SUDO gdebi --quiet --non-interactive $file 2>&1
        done
        ;;

    Fedora*)
        $SUDO rm *.src.rpm *.noarch.rpm 2>&1
        $SUDO dnf -y localinstall *.rpm 2>&1
        ;;

    RHEL*)
        $SUDO rm *.src.rpm *.noarch.rpm 2>&1
        $SUDO yum -y localinstall *.rpm 2>&1
        ;;

    SUSE*)
        $SUDO rm *.src.rpm *.noarch.rpm 2>&1
        $SUDO zypper --non-interactive install *.rpm 2>&1
        ;;

    Ubuntu*)
        for file in *.deb; do
            $SUDO gdebi --quiet --non-interactive $file 2>&1
        done
        ;;

    *)
        echo "$BB_NAME unknown platform" 2>&1
        ;;
    esac
}

while getopts vs:z: FLAG; do
    case "$FLAG" in
      v)
        VERBOSE=1
        ;;
      z)
        ZFS_TAG="$OPTARG"
        ;;
      s)
        SPL_TAG="$OPTARG"
        ;;
    esac
done
shift $((OPTIND-1))

if [ -f /etc/buildbot_spl ] && [ -f /etc/buildbot_zfs ]; then
  message "spl and zfs already installed. Skipping..."
  exit 3
fi

BUILD_ROOT=`mktemp -d`
MAKE_FLAGS="pkg"
CONFIG_OPTIONS=""

# enter build root
pushd ${BUILD_ROOT} &>/dev/null

if [ ! -f /etc/buildbot_spl ]; then
  message " == REPO ${GIT_SPL} TAG ${SPL_TAG} =="
  git clone ${GIT_SPL} ./spl || die "Failed to get SPL source"

  pushd spl &>/dev/null
  git checkout ${SPL_TAG} || die "SPL checkout failed"
  sh autogen.sh || die "SPL autogen failed"
  ./configure $CONFIG_OPTIONS || die "SPL configure failed"
  make $MAKE_FLAGS || die "SPL make pkg failed"

  install_packages

  sudo touch /etc/buildbot_spl
  popd &>/dev/null
fi

if [ ! -f /etc/buildbot_zfs ]; then
  message "== REPO ${GIT_ZFS} TAG ${ZFS_TAG} =="
  git clone ${GIT_ZFS} ./zfs || die "Failed to get ZFS source"
  pushd zfs &>/dev/null
  git checkout ${ZFS_TAG} || die "ZFS checkout failed"
  sh autogen.sh || die "ZFS autogen failed"
  ./configure $CONFIG_OPTIONS || die "ZFS configure failed"
  make $MAKE_FLAGS || die "ZFS make rpm failed"

  install_packages

  sudo touch /etc/buildbot_zfs
  popd &>/dev/null
fi

popd &>/dev/null

cleanup

exit 0
