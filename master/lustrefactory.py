# -*- python -*-
# ex: set syntax=python:

from buildbot.plugins import util
from buildbot.steps.source.gerrit import Gerrit
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import Configure
from buildbot.steps.shell import SetPropertyFromCommand 
from buildbot.steps.transfer import FileUpload
from buildbot.steps.trigger import Trigger
from buildbot.status.results import SUCCESS 
from buildbot.status.results import FAILURE 
from buildbot.status.results import SKIPPED 
from buildbot.status.results import WARNINGS

def do_step_build(step, name):
    props = step.build.getProperties()
    if props.hasProperty(name) and props[name] == "yes":
        return True
    else:
        return False

def do_step_zfs(step):
    return do_step_build(step, 'buildzfs')

def do_step_installdeps(step):
    return do_step_build(step, 'installdeps')

def hide_if_skipped(results, step):
    return results == SKIPPED

def hide_except_error(results, step):
    return results in (SUCCESS, SKIPPED)

@util.renderer
def dependencyCommand(props):
    args = ["runurl"]
    bb_url = props.getProperty('bburl')
    args.extend([bb_url + "bb-dependencies.sh"])
    return args

@util.renderer
def buildzfsCommand(props):
    args = ["runurl"]
    bb_url = props.getProperty('bburl')
    args.extend([bb_url + "bb-build-zfs-pkg.sh"])

    spltag = props.getProperty('spltag')
    if spltag:
        args.extend(["-s", spltag])

    zfstag = props.getProperty('zfstag')
    if zfstag:
        args.extend(["-z", zfstag])

    return args

@util.renderer
def buildCommand(props):
    args = ["runurl"]
    bb_url = props.getProperty('bburl')

    style = props.getProperty('buildstyle')
    if  style == "srpm":
        args.extend([bb_url + "bb-build-lustre-srpm.sh"])
    elif style == "deb":
        args.extend([bb_url + "bb-build-lustre-pkg.sh", "-m", "debs"])
    elif style == "rpm":
        args.extend([bb_url + "bb-build-lustre-pkg.sh", "-m", "rpms"])
    else:
        args.extend([bb_url + "bb-build-lustre-pkg.sh"])

    with_zfs = props.getProperty('withzfs')
    if with_zfs and with_zfs == "yes":
        args.extend(["-z"])

    with_ldiskfs = props.getProperty('withldiskfs')
    if with_ldiskfs and with_ldiskfs == "yes":
        args.extend(["-l"])

    return args

def createTarballFactory(gerrit_repo):
    """ Generates a build factory for a tarball generating builder.
    Returns:
        BuildFactory: Build factory with steps for generating tarballs.
    """
    bf = util.BuildFactory()

    # Pull the patch from Gerrit
    bf.addStep(Gerrit(
        repourl=gerrit_repo,
        workdir="build/lustre",
        mode="full",
        method="fresh",
        retry=[60,60],
        timeout=3600,
        logEnviron=False,
        getDescription=True,
        haltOnFailure=True,
        description=["cloning"],
        descriptionDone=["cloned"]))

    # make tarball
    bf.addStep(ShellCommand(
        command=['sh', './autogen.sh'],
        description=["autogen"],
        descriptionDone=["autogen"],
        workdir="build/lustre"))

    bf.addStep(Configure(
        command=['./configure', '--enable-dist'],
        workdir="build/lustre"))

    bf.addStep(ShellCommand(
        command=['make', 'dist'],
        description=["making dist"],
        descriptionDone=["make dist"],
        workdir="build/lustre"))

    # upload it to the master
    bf.addStep(SetPropertyFromCommand(
        command=['sh', '-c', 'echo *.tar.gz'],
        property='tarball',
        workdir="build/lustre",
        hideStepIf=hide_except_error,
        haltOnFailure=True))

    bf.addStep(FileUpload(
        workdir="build/lustre",
        slavesrc=util.Interpolate("%(prop:tarball)s"),
        masterdest=util.Interpolate("public_html/buildproducts/%(prop:event.change.number)s/%(prop:event.patchSet.number)s/%(prop:tarball)s"),
        url=util.Interpolate("http://%(prop:bbmaster)s/buildproducts/%(prop:event.change.number)s/%(prop:event.patchSet.number)s/%(prop:tarball)s"),
        urlText="tarball"))

    return bf

def createBuildFactory(gerrit_repo):
    """ Generates a build factory for a standard lustre builder.
    Args:
        gerrit_repo (string): Gerrit repo url
    Returns:
        BuildFactory: Build factory with steps for a standard lustre builder.
    """
    bf = util.BuildFactory()

    # update dependencies
    bf.addStep(ShellCommand(
        command=dependencyCommand,
        decodeRC={0 : SUCCESS, 1 : FAILURE, 2 : WARNINGS, 3 : SKIPPED },
        haltOnFailure=True, logEnviron=False,
        doStepIf=do_step_installdeps,
        hideStepIf=hide_if_skipped,
        description=["installing dependencies"],
        descriptionDone=["installed dependencies"]))

    # build spl and zfs if necessary
    bf.addStep(ShellCommand(
        command=buildzfsCommand,
        decodeRC={0 : SUCCESS, 1 : FAILURE, 2 : WARNINGS, 3 : SKIPPED },
        haltOnFailure=True, logEnviron=False,
        doStepIf=do_step_zfs,
        hideStepIf=hide_if_skipped,
        description=["building spl and zfs"],
        descriptionDone=["built spl and zfs"]))

    # Pull the patch from Gerrit
    bf.addStep(Gerrit(
        repourl=gerrit_repo, workdir="build/lustre",
        mode="full", method="clobber", retry=[60,60], timeout=3600,
        logEnviron=False, getDescription=True, haltOnFailure=True,
        description=["cloning"], descriptionDone=["cloned"]))

    # Build Lustre 
    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=buildCommand,
        haltOnFailure=True, logEnviron=False,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        decodeRC={0 : SUCCESS, 1 : FAILURE, 2 : WARNINGS, 3 : SKIPPED },
        description=["building lustre"], descriptionDone=["built lustre"]))

    # TODO: upload build products
    # Primary idea here is to upload the build products to buildbot's public html folder
    # what should go in there so far: tarball, srpm (maybe?), and build products (for the testers to download)

    return bf
