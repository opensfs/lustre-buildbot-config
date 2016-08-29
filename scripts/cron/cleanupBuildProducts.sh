#!/bin/bash

# This script can be used by a cron job to clean up
# patch set build products that are older than 14 days old
# and it will also remove change folders that are empty

BUILDPRODDIR=$1

if [ ! -d $BUILDPRODDIR ]; then
    exit 0 
fi

pushd $BUILDPRODDIR

# clean up the patchset folders that were created more than 14 days ago
find -depth -regex "\./[0-9]+/[0-9]+" -type d -ctime +14 -print0 | xargs --null rm -rvf

# remove empty change folders
rmdir $BUILDPRODDIR/* 2>/dev/null

popd

exit 0
