#!/usr/bin/python2.6
#
# Copyright (c) SAS Institute Inc.
#
# All rights reserved.
#

import logging
import os 

from spanner import repo
from spanner.scm import wms
from spanner.scm import git
from spanner.scm import hg
from spanner.scm import local

logger = logging.getLogger(__name__)

class Controller(object):
    '''
    B{Controller} Methods for interacting with a control repo
    
    Types include: 

        - WMS
        - GIT
        - HG    -- Not Implemented
        - LOCAL -- Not Implemented

    @param base: base uri for repo
    @type base: string
    @param path: path to the repo 
    @type path: string
    @keyword branch: branch name (defaults to master)
    @type branch: string 
    @keyword rev: commit revision (defaults to None)
    @type rev: string
    '''

    _registry = {}
    
    @classmethod
    def register(cls, klass):
        cls._registry[klass.ControllerType] = klass

    @classmethod
    def create(cls, controltype, *args, **kwargs):
        return cls._registry.get(controltype)(*args, **kwargs)

class BaseController(object):

    CONTROLLERS = ('WMS', 'GIT', 'HG', 'LOCAL')

    def __init__(self, base, path, branch=None, rev=None): 
        self.base = base       
        self.path = path
        self.branch = branch
        self.rev = rev
        self.repos = {} 
    
    def _getUri(self):
        '''
        Override
        '''
        return

    uri = property(_getUri)

    def updatecache(self):
        '''
        Override depending on Controller Type
        '''
        pass

    def check(self):
        '''
        Override depending on Controller Type
        returns True or False
        '''
        raise NotImplementedError

    def reader(self):
        '''
        Override depending on Controller Type
        '''
        raise NotImplementedError

    def latest(self):
        '''
        Return latest commit hash from the head of the branch        
        Override depending on Controller Type
        '''
        raise NotImplementedError

    def freeze(self, filename=None):
        '''
        Freeze scm revision for consistency
        Override depending on Controller Type
        '''
        # Set self.ctrl.revision based on some criteria
        revision = self.ctrl.setRevision(filename)
        return revision

    def checkout(self):
        '''
        Override depending on Controller Type
        '''
        pass

    def snapshot(self, directory, subtree=None):
        '''
        Override depending on Controller Type
        Snapshot a repo into a directory
        Not a live repo
        '''
        if not self.ctrl:
            raise NotImplementedError
        self.updatecache()
        self.ctrl.snapshot(directory, subtree)

    def findrepos(self):
        '''
        find control and read it
        clone all the repos
        '''
        return self.reader()



class WmsController(BaseController):
    ControllerType = 'WMS'

    def __init__(self, base, path, branch=None, rev=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.reposet = set()
        self.revfile = 'revision.txt'
        self.ctrl = wms.WmsRepository(self.base, self.path, self.branch)
        if rev:
            self.ctrl.revision = rev

    @property
    def revision(self):
        return self.ctrl.revision

    def setExactRevision(self, rev):
        self.ctrl.setRevision(rev=rev)

    def _getUri(self):
        return self.ctrl.getGitUri()

    uri = property(_getUri)

    def reader(self):
        # Default to reading local rev file
        if os.path.exists(self.revfile):
            data = self.ctrl.parseRevisionsFromFilename(self.revfile)
        else:
            data = self.ctrl.parseRevisionsFromUri()
        for name, info in data.iteritems():
            r = repo.Repo(name=name)
            r.update(info)
            self.reposet.add(r)
        return self.reposet

    def check(self):
        # FIXME MAYBE
        # Assuming if I can talk to wms I can snapshot from wms
        heads = self.ctrl.parseRevisionsFromUri(self.ctrl.poll)
        if heads:
            return True
        return False

    def latest(self):
        # TODO Use revisions.txt file to set revision and return that.
        return self.ctrl.getTip()

Controller.register(WmsController)

class GitController(BaseController):

    ControllerType = 'GIT'

    def __init__(self, base, path, branch=None, rev=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.repos = {}
        self._uri = '/'.join([self.base, self.path])
        self.ctrl = git.GitRepository(self._uri, self.branch)
        self.gitcmds = git.GitCommands()
        if rev:
            self.ctrl.revision = rev

    @property
    def revision(self):
        return self.ctrl.revision

    def check(self):
        heads = self.gitcmds.ls_remote(self._uri, self.branch)
        if heads:
            return True
        return False
    
    def compare_heads(self, test):
        heads = self.gitcmds.ls_remote(self._uri, self.branch)
        for head, commit in heads.items():
            if commit == test:
                return True
        return False

    def latest(self):
        HEAD = 'HEAD'
        if self.branch:
            HEAD = 'refs/heads/' + self.branch
        heads = self.gitcmds.ls_remote(self._uri, self.branch)
        return heads.get(HEAD)

    def updatecache(self):
        self.ctrl.updateCache()


Controller.register(GitController)

class HgController(BaseController):

    ControllerType = 'HG'

    def __init__(self, base, path, branch=None, rev=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.repos = {}
        self._uri = '/'.join([self.base, self.path])
        self.ctrl = hg.HgRepository(self._uri, self.branch)
        if rev:
            self.ctrl.revision = rev

    @property
    def revision(self):
        return self.ctrl.revision

    def updatecache(self):
        self.ctrl.updateCache()

Controller.register(HgController)

class LocalController(BaseController):

    ControllerType = 'LOCAL'

    def __init__(self, base, path, branch=None, rev=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.repos = {} 
        self._uri = os.path.join(self.base, self.path)
        self.ctrl = local.LocalRepository(self._uri, self.branch)
        if rev:
            self.ctrl.revision = rev

    @property
    def revision(self):
        return self.ctrl.revision

    def check(self):
        return os.path.exists(self._uri)

    def read(self):
        pass

    def readControlYaml(self, path):
        #FILE IS IN YAML 
        # pick up file
        # parse
        # make dict
        from yaml import load
        control = {}
        try:
            logger.info('Reading control file from %s' % path)
            stream = file(path, 'r')
            control = load(stream)
        except IOError, e:
            raise IOError, e
        return control


Controller.register(LocalController)
