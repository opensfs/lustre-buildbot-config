# -*- python -*-
# ex: set syntax=python:

from buildbot.plugins import util
from buildbot.steps.source.gerrit import Gerrit
from buildbot.steps.shell import ShellCommand, Configure, SetPropertyFromCommand
from buildbot.steps.master import SetProperty
from buildbot.steps.transfer import FileUpload, FileDownload, DirectoryUpload
from buildbot.steps.trigger import Trigger
from buildbot.status.results import SUCCESS, FAILURE, SKIPPED, WARNINGS 

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

def do_step_collectpacks(step):
    return do_step_if_value(step, 'buildstyle', 'rpm') or do_step_if_value(step, 'buildstyle', 'deb')

def do_step_buildrepo(step):
    return do_step_if_value(step, 'buildstyle', 'rpm')

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

    return args

@util.renderer
def makeCmd(props):
    args = ["sh", "-c"]
    style = props.getProperty('buildstyle')

    if style == "deb":
        args.extend(["make -j$(nproc) debs"])
    elif style == "rpm":
        args.extend(["make -j$(nproc) rpms"])
    else:
        args.extend(["make -j$(nproc)"])

    return args

@util.renderer
def collectProductsCmd(props):
    # put all binaries into a deliverables folder so DirectoryUpload can be used
    args = ["sh", "-c"]
    style = props.getProperty('buildstyle')
    arch = props.getProperty('arch')

    if style == "deb":
        args.extend(["mkdir ./deliverables && mv *.deb ./deliverables"])
    elif style == "rpm":
        mvcmd = "mkdir -p ./deliverables/{SRPM,%s/kmod} && mv $(ls *.rpm | grep -v *.src.rpm) ./deliverables/%s/kmod && mv *.src.rpm ./deliverables/SRPM" % (arch, arch)
        args.extend([mvcmd])
    else:
        args = []

    return args

def getChangeDirectory(props):
    # change directory is dependent on what we are building from
    category = props.getProperty('category')

    if category == 'patchset':
        # for patchsets, build products go into changeid/patchsetid
        change = props.getProperty('event.change.number')
        patchset = props.getProperty('event.patchSet.number')
        return ('%s/%s/' % (change, patchset))
    elif category == 'tag':
        # for tags, build products go into tags/<tag>
        tag = props.getProperty('branch')
        tag = tag.replace('refs/tags/', '')
        return ('tags/%s/' % (tag))

    return ''

def getBaseUrl(props):
    # generate the base url for build products of a change
    bb_url = props.getProperty('bbmaster')
    url = "http://%s/buildproducts/" % bb_url
    url += getChangeDirectory(props)
    return url

def getBaseMasterDest(props):
    # generate the base directory on the master for build products of a change
    masterdest = "public_html/buildproducts/"
    masterdest += getChangeDirectory(props)
    return masterdest

@util.renderer
def buildRepoCmd(props):
    # generate a repository to be sent to the build master
    # currently only support RPM based platforms
    args = ["sh", "-c"]
    style = props.getProperty('buildstyle')
    arch = props.getProperty('arch')
    distro = props.getProperty('distro')
    distrover = props.getProperty('distrover')
    url = getBaseUrl(props)
    url += ('%s/%s' % (distro, distrover))

    if style == "deb":
        args = []
    elif style == "rpm":
        # call create repo for the SRPM directory
        # call create repo for this architecture
        # generate a lustre.repo file for public consumption
        repocmd = "createrepo SRPM && createrepo %s/kmod && printf \"[lustre-SRPM]\nname=lustre-SRPM\nbaseurl=%s/SRPM/\nenabled=1\ngpgcheck=0\n\n[lustre-RPM]\nname=lustre-RPM\nbaseurl=%s/%s/kmod/\nenabled=1\ngpgcheck=0\" > lustre.repo" % (arch, url, url, arch)
        args.extend([repocmd])
    else:
        args = []

    return args

@util.renderer
def tarballMasterDest(props):
    # tarball exists in the top level of a change's directory
    tarball = props.getProperty('tarball')
    masterdest = getBaseMasterDest(props)
    masterdest += tarball
    return masterdest

@util.renderer
def tarballUrl(props):
    # tarball exists in the top level of a change's directory
    tarball = props.getProperty('tarball')
    url = getBaseUrl(props)
    url += tarball
    return url

@util.renderer
def repoMasterDest(props):
    # create a repo for each distro and distro version combination
    distro = props.getProperty('distro')
    distrover = props.getProperty('distrover')
    masterdest = getBaseMasterDest(props)
    masterdest += ('%s/%s' % (distro, distrover))
    return masterdest

@util.renderer
def repoUrl(props):
    # create a repo for each distro and distro version combination
    distro = props.getProperty('distro')
    distrover = props.getProperty('distrover')
    url = getBaseUrl(props)
    url += ('%s/%s' % (distro, distrover))
    return url

@util.renderer
def buildCategory(props):
    # category is generated by the scheduler name so we don't have to
    # look at the individual changes
    sched = props.getProperty('scheduler')
    if sched == 'master-patchset':
        return 'patchset'
    elif sched == 'tag-changes':
        return 'tag'

    return ''

def createTarballFactory(gerrit_repo):
    """ Generates a build factory for a tarball generating builder.
    Returns:
        BuildFactory: Build factory with steps for generating tarballs.
    """
    bf = util.BuildFactory()

    # are we building a tag or a patchset?
    bf.addStep(SetProperty(
        property='category',
        value=buildCategory, 
        hideStepIf=hide_except_error))

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
        masterdest=tarballMasterDest,
        url=tarballUrl))

    # trigger our builders to generate packages
    bf.addStep(Trigger(
        schedulerNames=["package-builders"],
        copy_properties=['tarball', 'category'],
        waitForFinish=False))

    return bf

def createPackageBuildFactory():
    """ Generates a build factory for a lustre tarball builder.
    Returns:
        BuildFactory: Build factory with steps for a lustre tarball builder.
    """
    bf = util.BuildFactory()

    # download our tarball and extract it
    bf.addStep(FileDownload(
        workdir="build/lustre",
        slavedest=util.Interpolate("%(prop:tarball)s"),
        mastersrc=tarballMasterDest))

    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=["tar", "-xvzf", util.Interpolate("%(prop:tarball)s"), "--strip-components=1"],
        haltOnFailure=True,
        logEnviron=False,
        lazylogfiles=True,
        description=["extracting tarball"],
        descriptionDone=["extract tarball"]))

    # update dependencies
    bf.addStep(ShellCommand(
        command=dependencyCommand,
        decodeRC={0 : SUCCESS, 1 : FAILURE, 2 : WARNINGS, 3 : SKIPPED },
        haltOnFailure=True,
        logEnviron=False,
        doStepIf=do_step_installdeps,
        hideStepIf=hide_if_skipped,
        description=["installing dependencies"],
        descriptionDone=["installed dependencies"]))

    # build spl and zfs if necessary
    bf.addStep(ShellCommand(
        command=buildzfsCommand,
        decodeRC={0 : SUCCESS, 1 : FAILURE, 2 : WARNINGS, 3 : SKIPPED },
        haltOnFailure=True,
        logEnviron=False,
        doStepIf=do_step_zfs,
        hideStepIf=hide_if_skipped,
        description=["building spl and zfs"],
        descriptionDone=["built spl and zfs"]))

    # Build Lustre 
    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=configureCmd,
        haltOnFailure=True,
        logEnviron=False,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        description=["configuring lustre"],
        descriptionDone=["configure lustre"]))

    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=makeCmd,
        haltOnFailure=True,
        logEnviron=False,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        description=["making lustre"],
        descriptionDone=["make lustre"]))

    # Build Products
    bf.addStep(ShellCommand(
        workdir="build/lustre",
        command=collectProductsCmd,
        haltOnFailure=True,
        logEnviron=False,
        doStepIf=do_step_collectpacks,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        description=["collect deliverables"],
        descriptionDone=["collected deliverables"]))

    # Build repo
    bf.addStep(ShellCommand(
        workdir="build/lustre/deliverables",
        command=buildRepoCmd,
        haltOnFailure=True,
        logEnviron=False,
        doStepIf=do_step_buildrepo,
        hideStepIf=hide_if_skipped,
        lazylogfiles=True,
        description=["building repo"],
        descriptionDone=["build repo"]))

    # Upload repo to master
    bf.addStep(DirectoryUpload(
        workdir="build/lustre",
        doStepIf=do_step_collectpacks,
        hideStepIf=hide_if_skipped,
        slavesrc="deliverables",
        masterdest=repoMasterDest,
        url=repoUrl))

    # Cleanup
    bf.addStep(ShellCommand(
        workdir="build",
        command=["sh", "-c", "rm -rvf *"],
        haltOnFailure=True,
        logEnviron=False,
        lazylogfiles=True,
        alwaysRun=True,
        description=["cleaning up"],
        descriptionDone=["clean up"]))

    return bf

