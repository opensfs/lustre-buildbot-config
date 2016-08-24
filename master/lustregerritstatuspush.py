from buildbot.status.status_gerrit import GerritStatusPush
from twisted.internet import reactor

class LustreGerritStatusPush(GerritStatusPush):

    def __init__(self, notify="OWNER", **kwargs):
        self.gerrit_notify = notify

        GerritStatusPush.__init__(self, **kwargs)

    def sendCodeReview(self, project, revision, result):
        gerrit_version = self.getCachedVersion()
        if gerrit_version is None:
            self.callWithVersion(lambda: self.sendCodeReview(project, revision,
                                                             result))
            return

        command = self._gerritCmd("review", "--project %s" % str(project))

        if self.gerrit_notify is not None:
            command.extend(["--notify %s" % str(self.gerrit_notify)])

        message = result.get('message', None)
        if message:
            command.append("--message '%s'" % message.replace("'", "\""))

        labels = result.get('labels', None)
        if labels:
            assert gerrit_version
            if gerrit_version < LooseVersion("2.6"):
                add_label = _old_add_label
            else:
                add_label = _new_add_label

            for label, value in labels.items():
                command.extend(add_label(label, value))

        command.append(str(revision))
        print command
        reactor.spawnProcess(self.LocalPP(self), command[0], command)
