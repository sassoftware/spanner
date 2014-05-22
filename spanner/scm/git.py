#
# Copyright (c) SAS Institute Inc.
#
# All rights reserved.
#



'''
Helper functions for dealing with git repositories.
'''

import logging
import os
import subprocess
from .. import scm

log = logging.getLogger(__name__)

class GitCommands(object):

    def __init__(self, cachedir=None):
        self.cachedir = cachedir

    def run_git(self, cmd, directory=None):
        if directory:
            log.debug("(cd '%s'; %s)", directory, " ".join(cmd))
        else:
            log.debug("%s", " ".join(cmd))
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=directory)
        log.debug
        stdout, stderr = p.communicate()
        if p.returncode:
            raise scm.ScmError(p.returncode, stderr, stdout)
        return stdout

    def ls_remote(self, uri, branch=None):
        cmd = ['git', 'ls-remote', uri]
        if branch:
            cmd.append(branch)
        return self.run_git(cmd)

    def ls_tree(self, branch):
        cmd = ['git', 'ls-tree', '-r', '--name-only', branch]
        return self.run_git(cmd)

    def show_file(self, path):
        uri = '''%s:%s''' % (self.branch, path)
        cmd = ['git', '--no-pager', 'show', uri]
        return self.run_git(cmd)

    def remote_v(self, path):
        cmd = ['git', 'remote', '-v']
        return self.run_git(cmd, path)

    def tags(self, path, msg=None):
        '''
        cd path
        git tag
        git tag -a -m "foo.bar"
        '''
        cmd = ['git', 'tag']
        if msg:cmd = cmd + ['-a', '-m', msg]
        return self.run_git(cmd, path)


    def show(self, path, tag=None):
        '''
        cd path
        git show
        git show <tag>
        ''' 
        cmd = ['git', 'show']
        if tag:cmd.append(tag)
        return self.run_git(cmd, path)

    def set_globals(self, aliases):
        '''
        Where aliases is a dict of attribute and value
        {'alias.co': 'checkout', 'user.name': 'Joe', 
            'user.email': 'j@b.com'}
        '''
        config = ['git', 'config', '--global']
        results = {}
        for attr,value in aliases.iteritems():
            results.setdefault(attr, self.run_git(config + [attr,value]))
        return results

    def checkout(self, path, branch):
        '''
        cd path
        git checkout -b <branch>
        '''
        cmd = ['git', 'checkout']
        if branch:
            cmd.extend(['-b' , branch])
        return self.run_git(cmd, path)

    def branch(self, path, branch=None):
        '''
        if branch is None
        gir branch
        else
        git branch -b <branch>
        '''
        cmd = ['git', 'branch']
        if branch:
            cmd.extend(['-b' , branch])
        return self.run_git(cmd, path)

    def pull(self, path, branch=None, withPush=False):
        '''
        cd path
        git pull
        '''
        cmd = ['git', 'pull']
        if branch:
            cmd.extend(['--ff-only', 'origin', 'refs/heads/%s' % branch])
        ret = self.run_git(cmd, path)
        if not withPush:
            return ret
        cmd = [ 'git', 'push', 'origin' ]
        return self.run_git(cmd, path)

    def clone(self, uri, branch=None, clonedir=None, path=None):
        '''
        git clone -b <branch> <uri> <dir>
        '''
        cmd = ['git', 'clone']
        if branch:
            cmd.extend(['-b' , branch])
        cmd.append(uri)
        if clonedir:cmd.append(clonedir)
        log.info("%s", " ".join(cmd))
        return self.run_git(cmd, path)


class GitRepository(scm.ScmRepository):

    def __init__(self, uri, branch, cache='_cache'):
        self.uri = uri
        self.branch = branch
        self.path = self.uri.split('//', 1)[-1]
        self.path = self.path.replace('/', '_')
        self.repo_dir = os.path.join(cache, self.path, 'git')

    def isLocal(self):
        return self.uri.startswith('/') or self.uri.startswith('file:')

    def getTip(self):
        self.updateCache()
        p = subprocess.Popen(
            ['git', 'rev-parse', self.branch],
            stdout=subprocess.PIPE,
            cwd=self.repo_dir,
            )
        stdout, stderr = p.communicate()
        if p.returncode:
            msg = "git exited with status %s" % p.returncode
            raise scm.ScmError(p.returncode, stderr, stdout, msg)
        rev = stdout.split()[0]
        assert len(rev) == 40
        return rev

    def updateCache(self):
        # Create the cache repo if needed.
        if not os.path.isdir(self.repo_dir):
            os.makedirs(self.repo_dir)
        if not (os.path.isdir(self.repo_dir + '/refs')
                or os.path.isdir(self.repo_dir + '/.git/refs')):
            subprocess.check_call(
                ['git', 'init', '-q', '--bare'],
                cwd=self.repo_dir,
                )
        subprocess.check_call(
            ['git', 'fetch', '-q', self.uri, '+%s:%s' % (
                    self.branch, self.branch)],
            cwd=self.repo_dir,
            )

    def snapshot(self, workDir, subtree):
        p1 = subprocess.Popen(
            ['git', 'archive', '--format=tar', self.revision, subtree], 
            stdout=subprocess.PIPE, 
            cwd=self.repoDir
            )

        p2 = subprocess.Popen(['tar', '-x'], stdin=p1.stdout, cwd=workDir)
        p1.stdout.close()  # remove ourselves from between git and tar
        p1.wait()
        p2.wait()
        if p1.returncode:
            raise RuntimeError("git exited with status %s" % p1.returncode)
        if p2.returncode:
            raise RuntimeError("tar exited with status %s" % p1.returncode)

    def setRevision(self, rev):
        super(GitRepository, self).setRevision(rev)
        if 'branch' in rev:
            self.branch = rev['branch']
        if 'uri' in rev:
            self.uri = rev['uri']


    def getAction(self, extra=''):
        return 'addGitSnapshot(%r, branch=%r, tag=%r%s)' % (
                self.uri, self.branch, self.getShortRev(), extra)

