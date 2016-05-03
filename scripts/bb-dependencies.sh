#!/bin/bash

# Check for a local cached configuration.
if test -f /etc/buildslave; then
    . /etc/buildslave
else
   echo "Missing configuration /etc/buildslave.  Assuming dependencies are"
   echo "already satisfied and this is a persistent buildslave."
   exit 0
fi

set -x

case "$BB_NAME" in
Amazon*)
    # Required development packages.
    sudo yum -y install kernel-devel-$(uname -r) \
        kernel-debuginfo-$(uname -r) \
        zlib-devel libuuid-devel libblkid-devel libselinux-devel \
        xfsprogs-devel libattr-devel libacl-devel

    # Required utilties.
    sudo yum -y install git rpm-build wget curl lsscsi parted attr dbench \
        watchdog createrepo python python-pip python-docutils xfig transfig
    ;;

CentOS*)
    if cat /etc/redhat-release | grep -Eq "6."; then
        sudo yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm
        #sudo yum -y localinstall --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el6.noarch.rpm
    elif cat /etc/redhat-release | grep -Eq "7."; then
        sudo yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
        #sudo yum -y localinstall --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el7.noarch.rpm
    fi

    # Required development tools.
    sudo yum -y install gcc make autoconf libtool 

    # Development packages
    sudo yum -y --enablerepo=base-debuginfo install kernel-devel-$(uname -r) \
        kernel-debuginfo-$(uname -r) \
        zlib-devel libuuid-devel libblkid-devel libselinux-devel \
        xfsprogs-devel libattr-devel libacl-devel

    # Required utilties.
    sudo yum -y install git rpm-build wget curl lsscsi parted attr dbench bc \
        watchdog createrepo mock python python-docutils mdadm xfig transfig

    # add user to the mock group
    sudo usermod -a -G mock buildbot
    ;;

Debian*)
    #sudo apt-get --yes install lsb-release
    #sudo wget --quiet http://archive.zfsonlinux.org/debian/pool/main/z/zfsonlinux/zfsonlinux_6_all.deb
    #sudo dpkg -i zfsonlinux_6_all.deb

    # Required development tools.
    sudo apt-get --yes install build-essential autoconf libtool libtool-bin

    # Development packages
    sudo apt-get --yes install linux-headers-$(uname -r) \
        kernel-debuginfo-$(uname -r) \
        zlib1g-dev uuid-dev libblkid-dev libselinux-dev \
        xfslibs-dev libattr1-dev libacl1-dev

    # Required utilties.
    sudo apt-get --yes install git alien fakeroot wget curl bc \
        lsscsi parted gdebi attr dbench watchdog createrepo \
        python python-pip python-docutils xfig transfig
    ;;

Fedora*)
    #sudo yum install --nogpgcheck http://archive.zfsonlinux.org/fedora/zfs-release$(rpm -E %dist).noarch.rpm

    # Required development tools.
    sudo dnf -y install gcc autoconf libtool

    # Development packages
    sudo dnf -y install kernel-devel-$(uname -r) 
        kernel-debuginfo-$(uname -r) \
        zlib-devel libuuid-devel libblkid-devel libselinux-devel \
        xfsprogs-devel libattr-devel libacl-devel

    # Required utilties.
    sudo dnf -y install git rpm-build wget curl lsscsi parted attr dbench \
        watchdog createrepo mock python python-pip python-docutils xfig transfig

    # add user to the mock group
    sudo usermod -a -G mock buildbot
    ;;

RHEL*)
    if cat /etc/redhat-release | grep -Eq "6."; then
        EXTRA_REPO="--enablerepo=rhui-REGION-rhel-server-releases-optional"
        sudo yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm
        #sudo yum -y localinstall --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el6.noarch.rpm
    elif cat /etc/redhat-release | grep -Eq "7."; then
        EXTRA_REPO="--enablerepo=rhui-REGION-rhel-server-optional"
        sudo yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
        #sudo yum -y localinstall --nogpgcheck http://archive.zfsonlinux.org/epel/zfs-release.el7.noarch.rpm
    else
        EXTRA_REPO=""
    fi

    # Required development tools.
    sudo yum -y install gcc autoconf libtool

    # Development packages
    sudo yum -y $EXTRA_REPO --enablerepo=rhel-debuginfo install kernel-devel-$(uname -r) \
        kernel-debuginfo-$(uname -r) \
        zlib-devel libuuid-devel libblkid-devel libselinux-devel \
        xfsprogs-devel libattr-devel libacl-devel

    # Required utilties.
    sudo yum -y $EXTRA_REPO install git rpm-build wget curl lsscsi \
        parted attr dbench bc watchdog createrepo mock python \
        python-pip python-docutils mdadm xfig transfig

    # add user to the mock group
    sudo usermod -a -G mock buildbot
    ;;

SUSE*)
    # assume SUSE 12 for now
    #sudo zypper --non-interactive ar -f http://download.opensuse.org/repositories/filesystems/SLE_12/ OpenSUSE-SLE12

    # Required development tools.
    sudo zypper --non-interactive install gcc autoconf libtool

    # Required utilties.
    sudo zypper --non-interactive install git rpm-build wget curl \
        lsscsi parted attr createrepo python python-pip python-docutils xfig transfig

    # Required development packages.
    sudo zypper --non-interactive --plus-content debug install \
        kernel-devel kernel-default-debuginfo \
        zlib-devel libuuid-devel libblkid-devel libselinux-devel \
        xfsprogs-devel libattr-devel libacl-devel kernel-source
    ;;

OpenSUSE*)
    # assume SUSE 12 for now
    #sudo zypper --non-interactive ar -f http://download.opensuse.org/repositories/filesystems/SLE_12/ OpenSUSE-SLE12

    # Required development tools.
    sudo zypper --non-interactive install gcc autoconf libtool

    # Required utilties.
    sudo zypper --non-interactive install git rpm-build wget curl \
        lsscsi parted attr createrepo python python-pip python-docutils xfig transfig

    # Required development packages.
    sudo zypper --non-interactive --plus-content debug install \
        kernel-devel kernel-default-debuginfo \
        zlib-devel libuuid-devel libblkid-devel libselinux-devel \
        xfsprogs-devel libattr-devel libacl-devel kernel-source
    ;;

Ubuntu*)
    # Required development tools.
    sudo apt-get --yes install build-essential autoconf libtool \
        module-assistant libreadline-dev dpatch libsnmp-dev quilt

    # Required utilties.
    sudo apt-get --yes install git alien fakeroot wget curl \
        lsscsi parted gdebi attr dbench watchdog \
        python python-pip python-docutils xfig transfig

    # Required development libraries
    sudo apt-get --yes install linux-headers-$(uname -r) \
        linux-image-$(uname -r) \
        zlib1g-dev uuid-dev libblkid-dev libselinux-dev \
        xfslibs-dev libattr1-dev libacl1-dev
    ;;

*)
    echo "$BB_NAME unknown platform"
    ;;
esac
