# -*- python -*-
# ex: set syntax=python:

import itertools
import os

from buildbot import config
from twisted.internet import defer
from twisted.internet import utils
from twisted.python import log
from buildbot.util import epoch2datetime
from buildbot.changes.gitpoller import GitPoller

class LustreTagPoller(GitPoller):

    """This source polls a git repo for new tags and generates a change.

    This source will poll a remote git repository for new tags and finds changes
    to existing tags. Once a new or changed tag is found, a change is submitted to
    the build master. The poller maintains a set of previously seen tags and each
    tags associated revision (SHA). On each poll iteration, all references are
    checked against the prior set. A tag is considered new if it doesn't exist in
    the set. A tag is considered change when the tag has been seen but its revision
    has changed. The set is maintain in the buildbot master's database.

    If workdir is None, 'lustretagpoller-work' becomes the working directory for
    this poller. The branch and branches arguments are not accepted by this class."""

    def __init__(self, **kwargs):
        if kwargs.get('workdir') is None:
            kwargs['workdir'] = 'lustretagpoller-work'

        if kwargs.get('branch') or kwargs.get('branches'):
            config.error("LustreTagPoller: branch/branches is not a valid argument.")

        GitPoller.__init__(self, **kwargs)

    def describe(self):
        str = ('LustreTagPoller watching the remote git repository ' +
               self.repourl + ' for new tags')

        if not self.master:
            str += " [STOPPED - check log]"

        return str

    def _getRefs(self):
        """Collect and parse all local references"""

        d = self._dovccmd('show-ref', [])

        @d.addCallback
        def parseRefs(rows):
            refs = {}
            for row in rows.splitlines():
                sha, ref = row.split()

                if not self._filter_ref(ref):
                    refs[ref] = sha

            return refs

        return d

    def _filter_ref(self, ref):
        """Filter refs that are not tags"""
        return not ref.startswith("refs/tags/")

    @defer.inlineCallbacks
    def _process_change(self, ref, rev):
        """Determines if a tag should be submitted to build master as a change """
        # initial run, don't parse all history
        if not self.lastRev:
            return

        # if a tag has been previously seen, and it's revision hasn't changes, there's nothing to process
        if ref in self.lastRev and self.lastRev[ref] == rev:
            return

        log.msg('LustreTagPoller: processing %s(%s) from "%s"'% (ref, rev, self.repourl))

        dl = defer.DeferredList([
            self._get_commit_timestamp(rev),
            self._get_commit_author(rev),
            self._get_commit_files(rev),
            self._get_commit_comments(rev),
        ], consumeErrors=True)

        results = yield dl

        # check for failures
        failures = [r[1] for r in results if not r[0]]
        if failures:
            # just fail on the first error; they're probably all related!
            raise failures[0]

        timestamp, author, files, comments = [r[1] for r in results]
        yield self.master.addChange(
            author=author,
            revision=rev,
            files=files,
            comments=comments,
            when_timestamp=epoch2datetime(timestamp),
            branch=ref,
            category=self.category,
            project=self.project,
            repository=self.repourl,
            src='git')

    @defer.inlineCallbacks
    def poll(self):
        log.msg("LustreTagPoller: poll iteration started")
        if not os.path.exists(self.workdir):
            yield self._dovccmd('init', ['--bare', self.workdir])

        log.msg("LustreTagPoller: fetch --tags")
        yield self._dovccmd('fetch', ['--tags', self.repourl], path=self.workdir)

        newRefs = yield self._getRefs()

        log.msg("LustreTagPoller: processing tags")
        for ref, sha in newRefs.iteritems():
            yield self._process_change(ref, sha)

        self.lastRev.update(newRefs)
        yield self.setState('lastRev', self.lastRev)

        log.msg("LustreTagPoller: poll iteration complete")
