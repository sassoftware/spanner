#!/usr/bin/python2.6
#
# Copyright (c) SAS Institute Inc.
#
# All rights reserved.
#

import os
import logging
import urlparse

from spanner import repo
from spanner.scm import wms
from spanner.scm import git
from spanner.scm import hg

logger = logging.getLogger(__name__)

class Controller(object):
    _registry = {}
    
    @classmethod
    def register(cls, klass):
        cls._registry[klass.ControllerType] = klass

    @classmethod
    def create(cls, controltype, *args, **kwargs):
        return cls._registry.get(controltype)(*args, **kwargs)

class BaseController(object):

    CONTROLLERS = ('WMS', 'GIT', 'HG', 'LOCAL')

    def __init__(self, base, path, branch=None): 
        self.base = base       
        self.path = path
        self.branch = branch
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


    def checkout(self):
        '''
        Override depending on Controller Type
        '''
        pass

    def snapshot(self, directory):
        '''
        Override depending on Controller Type
        Snapshot a repo into a directory
        Not a live repo
        '''
        raise NotImplementedError

    def findrepos(self):
        '''
        find control and read it
        clone all the repos
        '''
        return self.reader()


class WmsController(BaseController):
    ControllerType = 'WMS'

    def __init__(self, base, path, branch=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.reposet = set()
        self.wms = wms.WmsRepository(self.base, self.path, self.branch)

    def _getUri(self):
        return self.wms.getGitUri()

    uri = property(_getUri)

    def reader(self):
        data = self.wms.parseRevisionsFromUri()
        for name, info in data.iteritems():
            repo = repo.Repo(name=name)
            repo.update(info)
            self.reposet.add(repo)
        return self.reposet


Controller.register(WmsController)

class GitController(BaseController):

    ControllerType = 'GIT'

    def __init__(self, base, path, branch=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.repos = {}
        self.uri = '/'.join(self.base, self.path)
        self.git = git.GitRepository(self.uri, self.branch)
        self.gitcmds = git.GitCommands()

    def check(self):
        heads = self.gitcmds.ls_remote(self.uri, self.branch)
        if heads:
            return True
        return False
    
    def compare_heads(self, test):
        heads = self.gitcmds.ls_remote(self.uri, self.branch)
        for head, commit in heads.items():
            if commit == test:
                return True
        return False

    def latest(self):
        commits = []
        heads = self.gitcmds.ls_remote(self.uri, self.branch)
        for head, commit in heads.items():
            commits.append(commit)
        return commits

    def updatecache(self):
        self.git.updateCache()

    def snapshot(self, directory):
        self.updatecache()
        self.git.snapshot(directory)

Controller.register(GitController)

class HgController(BaseController):

    ControllerType = 'HG'

    def __init__(self, base, path, branch=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.repos = {}


Controller.register(HgController)

class LocalController(BaseController):

    ControllerType = 'LOCAL'

    def __init__(self, base, path, branch=None):
        self.base = base
        self.path = path
        self.branch = branch
        self.repos = {} 


    def reader(self, path):
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
