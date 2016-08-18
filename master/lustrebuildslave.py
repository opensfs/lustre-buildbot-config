# -*- python -*-
# ex: set syntax=python:

import string
import random
import re
from password import *
from buildbot.plugins import util
from buildbot.buildslave import BuildSlave
from buildbot.buildslave.ec2 import EC2LatentBuildSlave

### BUILDER CLASSES
class LustreBuilderConfig(util.BuilderConfig):
    @staticmethod
    def nextSlave(builder, slaves):
        availableSlave = None

        for slave in slaves:
            # if we found an idle slave, immediate use this one
            if slave.isIdle():
                return slave

            # hold onto the first slave thats not spun up but free
            if availableSlave is None and slave.isAvailable():
                availableSlave = slave

        # we got here because there was no idle slave
        if availableSlave is not None:
            return availableSlave

        # randomly choose among all our busy slaves
        return (random.choice(slaves) if slaves else None)

    def __init__(self, mergeRequests=False, nextSlave=None, **kwargs):
        if nextSlave is None:
            nextSlave = LustreBuilderConfig.nextSlave

        util.BuilderConfig.__init__(self, nextSlave=nextSlave, 
                                    mergeRequests=mergeRequests, **kwargs)

### BUILD SLAVE CLASSES
class LustreEC2Slave(EC2LatentBuildSlave):
    default_user_data = """#!/bin/bash
set -e
set -x
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Ensure wget is available for runurl
if ! hash wget 2>/dev/null; then
    if hash apt-get 2>/dev/null; then
        apt-get --quiet --yes install wget
    elif hash dnf 2>/dev/null; then
        echo "keepcache=true"     >>/etc/dnf/dnf.conf
        echo "deltarpm=true"      >>/etc/dnf/dnf.conf
        echo "fastestmirror=true" >>/etc/dnf/dnf.conf
        dnf clean all
        dnf --quiet -y install wget
    elif hash yum 2>/dev/null; then
        yum --quiet -y install wget
    else
        echo "Unknown package managed cannot install wget"
    fi
fi

# Set our bb variables
export BB_MASTER='%s'
export BB_NAME='%s'
export BB_PASSWORD='%s'
export BB_URL='%s'

if [ -z "$BB_URL" ]; then
    export BB_URL="https://raw.githubusercontent.com/opensfs/lustre-buildbot-config/master/scripts/"
fi

# Get the runurl utility.
wget -qO/usr/bin/runurl $BB_URL/runurl
chmod 755 /usr/bin/runurl

# Run the bootstrap script
runurl $BB_URL/bb-bootstrap.sh"""

    @staticmethod
    def pass_generator(size=24, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def __init__(self, name, password=None, master='', url='', instance_type="m3.large",
                identifier=ec2_default_access, secret_identifier=ec2_default_secret,
                keypair_name=ec2_default_keypair_name, security_name='LustreBuilder',
                user_data=None, region="us-west-1", placement="b", max_builds=1,
                build_wait_timeout=60 * 30, spot_instance=True, max_spot_price=.08,
                price_multiplier=None, **kwargs):

        self.name = name

        tags = kwargs.get('tags')
        if not tags or tags is None:
            tags={
                "ENV"      : "DEV",
                "Name"     : "LustreBuilder",
                "ORG"      : "COMP",
                "OWNER"    : "Buildbot Admin <buildbot-admin@lustre.org>",
                "PLATFORM" :  name,
                "PROJECT"  : "Lustre",
            }

        if password is None:
            password = LustreEC2Slave.pass_generator()

        if user_data is None:
            user_data = LustreEC2Slave.default_user_data % (master, name, password, url)

        EC2LatentBuildSlave.__init__(
            self, name=name, password=password, instance_type=instance_type, 
            identifier=identifier, secret_identifier=secret_identifier, region=region,
            user_data=user_data, keypair_name=keypair_name, security_name=security_name,
            max_builds=max_builds, spot_instance=spot_instance, tags=tags,
            max_spot_price=max_spot_price, placement=placement,
            price_multiplier=price_multiplier, build_wait_timeout=build_wait_timeout, 
            **kwargs)

class LustreEC2SuseSlave(LustreEC2Slave):
    def __init__(self, name, **kwargs):
        LustreEC2Slave.__init__(self, name, max_spot_price="0.16",
                                     instance_type="m3.large",
                                     product_description="SUSE Linux (Amazon VPC)",
                                     **kwargs)

