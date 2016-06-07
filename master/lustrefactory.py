# -*- python -*-
# ex: set syntax=python:

from buildbot.plugins import util
from buildbot.steps.source.gerrit import Gerrit
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import Configure
from buildbot.steps.shell import SetPropertyFromCommand 
from buildbot.steps.transfer import FileUpload, FileDownload
from buildbot.steps.trigger import Trigger
from buildbot.status.results import SUCCESS 
from buildbot.status.results import FAILURE 
from buildbot.status.results import SKIPPED 
from buildbot.status.results import WARNINGS

def do_step_if_value(step, name, value):
    props = step.build.getProperties()
    if props.hasProperty(name) and props[name] == value:
        return True
    else:
        return False

def do_step_zfs(step):
    return do_step_if_value(step, 'buildzfs', 'yes')

def do_step_installdeps(step):
    return do_step_if_value(step, 'installdeps', 'yes')

def do_step_rpmbuild(step):
    return do_step_if_value(step, 'buildstyle', 'srpm')

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
def configureCmd(props):
    args = ["./configure"]
    style = props.getProperty('buildstyle')

    if style == "deb" or style == "rpm":
        with_zfs = props.getProperty('withzfs')
        if with_zfs and with_zfs == "yes":
            args.extend(["--with-zfs"])
        else:
            args.extend(["--without-zfs"])

        with_ldiskfs = props.getProperty('withldiskfs')
        if with_ldiskfs and with_ldiskfs == "yes":
            args.extend(["--enable-ldiskfs"])
        else:
            args.extend(["--disable-ldiskfs"])
    elif style == "srpm":
        args.extend(["--enable-dist"])

    return args

@util.renderer
def makeCmd(props):
    args = ["sh", "-c"]
    style = props.getProperty('buildstyle')

    if style == "srpm":
        args.extend(["make -j$(nproc) srpm"])
    elif style == "deb":
        args.extend(["make -j$(nproc) debs"])
    elif style == "rpm":
        args.extend(["make -j$(nproc) rpms"])
    else:
        args.extend(["make -j$(nproc)"])

    return args

@util.renderer
def rpmbuildCmd(props):
    args = ["sh", "-c"] 
    style = props.getProperty('buildstyle')
    zfsArg = "--without zfs"
    ldiskfsArg = "--without ldiskfs"

    if style == "srpm":
        with_zfs = props.getProperty('withzfs')
        if with_zfs and with_zfs == "yes":
            zfsArg = "--with zfs"

        with_ldiskfs = props.getProperty('withldiskfs')
        if with_ldiskfs and with_ldiskfs == "yes":
            ldiskfsArg = "--with ldiskfs"

    cmd = "rpmbuild --rebuild %s %s lustre-*.src.rpm" % (zfsArg, ldiskfsArg)
    args.extend([cmd])

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
        haltOnFailure=True,
        description=["autogen"],
        descriptionDone=["autogen"],
        workdir="build/lustre"))

    bf.addStep(Configure(
        command=['./configure', '--enable-dist'],
        workdir="build/lustre"))

    bf.addStep(ShellCommand(
        command=['make', 'dist'],
        haltOnFailure=True,
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
        url=util.Interpolate("http://%(prop:bbmaster)s/buildproducts/%(prop:event.change.number)s/%(prop:event.patchSet.number)s/%(prop:tarball)s")))

    # trigger our builders to generate packages
    bf.addStep(Trigger(
        schedulerNames=["package-builders"],
        set_properties={"tarball" : util.Interpolate("%(prop:tarball)s")},
        waitForFinish=False))

    return bf

def createPackageBuildFactory():
    """ Generates a build factory for a lustre tarball builder.
    Returns:
        BuildFactory: Build factory with steps for a lustre builder.
    """
    bf = util.BuildFactory()

    # download our tarball and extract it
    bf.addStep(FileDownload(
        workdir="build/lustre",
        slavedest=util.Interpolate("%(prop:tarball)s"),
        mastersrc=util.Interpolate("public_html/buildproducts/%(prop:event.change.number)s/%(prop:event.patchSet.number)s/%(prop:tarball)s")))

    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=["tar", "-xvzf", util.Interpolate("%(prop:tarball)s"), "--strip-components=1"],
        haltOnFailure=True, logEnviron=False,
        lazylogfiles=True,
        description=["extracting tarball"], descriptionDone=["extract tarball"]))

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

    # Build Lustre 
    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=configureCmd,
        haltOnFailure=True, logEnviron=False,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        description=["configuring lustre"], descriptionDone=["configure lustre"]))

    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=makeCmd,
        haltOnFailure=True, logEnviron=False,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        description=["making lustre"], descriptionDone=["make lustre"]))

    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=rpmbuildCmd,
        haltOnFailure=True, logEnviron=False,
        doStepIf=do_step_rpmbuild,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        description=["rpmbuilding lustre"], descriptionDone=["rpmbuild lustre"]))

    # TODO: upload build products
    # Primary idea here is to upload the build products to buildbot's public html folder
    # what should go in there so far: tarball, srpm (maybe?), and build products (for the testers to download)

    bf.addStep(ShellCommand(
        workdir="build",
        command=["sh", "-c", "rm -rf *"],
        haltOnFailure=True, logEnviron=False,
        lazylogfiles=True,
        alwaysRun=True,
        description=["cleaning up"],
        descriptionDone=["clean up"]))

    return bf
