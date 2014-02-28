'''
Helper functions for dealing with git repositories.
'''

import logging
import os
import subprocess

import scm

log = logging.getLogger(__name__)


class GitRepository(scm.ScmRepository):

    def __init__(self, cacheDir, uri, branch):
        self.uri = uri
        self.branch = branch

        dirPath = self.uri.split('//', 1)[-1]
        dirPath = dirPath.replace('/', '_')
        self.repoDir = os.path.join(cacheDir, dirPath, 'git')

    def isLocal(self):
        return self.uri.startswith('/') or self.uri.startswith('file:')


    def getTip(self):
        self.updateCache()
        p = subprocess.Popen(
            ['git', 'rev-parse', self.branch],
            stdout=subprocess.PIPE,
            cwd=self.repoDir,
            )
        stdout, _ = p.communicate()
        if p.returncode:
            raise RuntimeError("git exited with status %s" % p.returncode)
        rev = stdout.split()[0]
        assert len(rev) == 40
        return rev

    def updateCache(self):
        # Create the cache repo if needed.
        if not os.path.isdir(self.repoDir):
            os.makedirs(self.repoDir)
        if not (os.path.isdir(self.repoDir + '/refs')
                or os.path.isdir(self.repoDir + '/.git/refs')):
            subprocess.check_call(
                ['git', 'init', '-q', '--bare'],
                cwd=self.repoDir,
                )
        subprocess.check_call(
            ['git', 'fetch', '-q', self.uri, '+%s:%s' % (
                    self.branch, self.branch)],
            cwd=self.repoDir,
            )

    def checkout(self, workDir):
        p1 = subprocess.Popen(
            ['git', 'archive', '--format=tar', self.branch],
            stdout=subprocess.PIPE,
            cwd=self.repoDir,
            )
        p2 = subprocess.Popen(['tar', '-x'], stdin=p1.stdout, cwd=workDir)
        p1.stdout.close()  # remove ourselves from between git and tar
        p1.wait()
        p2.wait()
        if p1.returncode:
            raise RuntimeError("git exited with status %s" % p1.returncode)
        if p2.returncode:
            raise RuntimeError("tar exited with status %s" % p1.returncode)

    def ls_remote(self, uri, branch=None):
        cmd = ['git', 'ls-remote', uri]
        if branch:
            cmd.append(branch)
        stdout = self.run_git(cmd)
        heads = {}
        for head in stdout.splitlines():
            sha, name = head.split('\t')
            assert sha and name
            heads[name] = sha
        return heads

    def ls_tree(self, branch):
        cmd = ['git', 'ls-tree', '-r', '--name-only', branch]
        stdout = self.run_git(cmd)
        files = {}
        files[branch] = [x for x in stdout.splitlines() if x]
        return files

    def show_file(self, path):
        uri = '''%s:%s''' % (self.branch, path)
        cmd = ['git', '--no-pager', 'show', uri]
        return self.run_git(cmd)

    def run_git(self, cmd):
        directory = None
        if os.path.exists(self.repoDir):
            directory = self.repoDir
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, cwd=directory)
        stdout, _ = p.communicate()
        if p.returncode:
            raise RuntimeError("git exited with status %s" % p.returncode)
        return stdout

    def getAction(self, extra=''):
        return 'addGitSnapshot(%r, branch=%r, tag=%r%s)' % (
                self.uri, self.branch, self.revision, extra)
