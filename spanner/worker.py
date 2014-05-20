import logging
import os
import subprocess
import tempfile
import time
from collections import defaultdict


from . import config
from . import errors
from . import fetcher
from . import reader
from . import checker
from . import builder
from . import grouper
from . import controller

logger = logging.getLogger(__name__)


class Worker(object):

    def __init__(self, uri, branch=None, cfg=None, test=False):

        self.cfg = cfg
        self.test = test

        if not self.cfg:
            self.cfg = self.getcfg()
         
        if self.cfg.testOnly:
            logger.warn('testOnly set in config file ignoring commandline')
            self.test = self.cfg.testOnly

        self.tmpdir = self.cfg.tmpDir
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        assert os.path.exists(self.tmpdir)

        self.controller = self.create_controller(uri, branch)


        self.fetcher = fetcher.Fetcher(self.uri, self.controller, self.cfg)
        self.reader = reader.Reader(self.cfg, self.controller, self.test)
        self.checker = checker.Checker(self.cfg, self.controller, self.test)
        self.builder = builder.Builder(self.cfg, self.controller, self.test)
        self.grouper = grouper.Grouper(self.cfg, self.controller, self.test)

    def getcfg(self):
        logger.info('Loading default cfg')
        cfg = config.SpannerConfiguration()
        cfg.read()
        return cfg

    def create_controller(self, uri, branch=None):
        # Start with GIT
        ctrltype = 'GIT'
        paths = [ x for x in uri.split('/') if x ]
        pre = paths[0]
        if pre in [ 'http:', 'https:', 'ssh:', 'git:' ]:
            base = '//'.join(paths[:2])
            if base == self.cfg.wmsBase:
                ctrltype = 'WMS'
        else:
            base = '/'.join(paths[:2])
            ctrltype = 'LOCAL'
        path = '/'.join(paths[2:])
        # Silly but if we do not specify branch at command line 
        # then we assume it is master unless we can extract it 
        # from the end of a git uri
        if not branch:
            # TODO Use cfg option for this?
            branch = 'master'
            if len(path.split('?')) == 2:
                path, branch = path.split('?')
        self.base = base
        self.branch = branch
        self.cntrltype = ctrltype
        return controller.Controller.create(self.cntrltype,
                                                self.base,
                                                self.path,
                                                self.branch,
                                                )


    def fetch(self, uri):
        '''
        pass in location of the plans
        check out plans from repo
        return location of plans
        '''
        return self.fetcher(uri)
        

    def read(self, path):
        '''
        pass in path to plans
        return set of package objects
        '''
        return self.reader(path)

    def check(self, plans, force=[]):
        '''
        pass in set of package objects
        check controller for versions
        check conary for versions
        return set of package objects with build flag set
        '''
        # checker returns set of packages updated with conary version
        # and the build flag set if changed
        return self.checker(plans, force)

    def build(self, packageset):
        '''
        pass in set of package objects
        call bob for packages that need to be built
        record packages that were updated
        return updated set of package objects
        '''
        # builder returns set of packages updated with built flag set
        return self.builder(packageset)

    def group(self, packageset):
        '''
        pass in set of package objects
        look up conary versions
        make sure versions on label match versions in set()
        create a group with the specified versions of the packages
        cook group
        '''
        return self.grouper(packageset)

    def display(self, packageset):
        '''
        pass in set of package objects
        log built, groupname
        '''
        for pkg in packageset:
            print pkg.built
            print pkg.fail
            print pkg.group

    def main(self, force=[]):
        planpath = self.fetch(self.uri)
        plans = self.read(planpath)
        packageset = self.check(plans, force)
        packageset = self.build(packageset)
        packageset = self.group(packageset)
        self.display(packageset)


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

