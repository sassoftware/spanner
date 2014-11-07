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

logger = logging.getLogger(__name__)


class Worker(object):

    def __init__(self, uri, force=[], branch=None, cfgfile=None, test=False):

        self.uri = uri
        self.force = force
        self.cfgfile = cfgfile
        self.cfg = self.getDefaultConfig()
        self.test = test
        self.branch = branch
 
        if self.cfg.testOnly:
            logger.warn('testOnly set in config file ignoring commandline')
            self.test = self.cfg.testOnly

        self.tmpdir = self.cfg.tmpDir
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        assert os.path.exists(self.tmpdir)

    def getDefaultConfig(self, cfgFile=None):
        logger.info('Loading default cfg')
        if not cfgFile:
            cfgFile = self.cfgfile
        return config.SpannerConfiguration(config=cfgFile)

    def fetch(self):
        '''
        pass in location of the plans
        check out plans from repo
        return destination of plans
        '''
        fetch_plans = fetcher.Fetcher(self.uri, self.cfg, self.branch)
        return fetch_plans.fetch()

    def read(self, path):
        '''
        pass in path to plans
        return set of package objects
        '''
        read_plans = reader.Reader(path, self.cfg)
        return read_plans.read()

    def check(self, plans):
        '''
        pass in set of package objects
        check controller for versions
        check conary for versions
        return set of package objects with build flag set
        '''
        # checker returns set of packages updated with conary version
        # and the build flag set if changed
        changes = checker.Checker(plans, self.cfg, 
                            self.force, self.branch, self.test)
        return changes.check()

    def build(self, packageset, products=False):
        '''
        pass in set of package objects
        call bob for packages that need to be built
        record packages that were updated
        return updated set of package objects
        '''
        # builder returns set of packages updated with built flag set
        b = builder.Builder(packageset, self.cfg, self.test)
        if products:
            return b.buildProducts()
        return b.buildProjects()

    def group(self, packageset, plans=None):
        '''
        pass in set of package objects
        look up conary versions
        make sure versions on label match versions in set()
        create a group with the specified versions of the packages
        cook group
        '''
        g = grouper.Grouper(packageset, self.cfg, self.test, plans)
        return g.group()

    def display(self, packageset):
        '''
        pass in set of package objects
        log built, groupname
        '''
        pass

    def main(self):
        start = time.time()
        print "Begin gathering planpaths : %s" % start
        planpaths = self.fetch()
        end = time.time() - start
        print "End gathering planpaths : %s" % end
        #import epdb;epdb.st()
        plans = self.read(planpaths)
        #import epdb;epdb.st()
        packageset = self.check(plans)
        #import epdb;epdb.st()
        packageset = self.build(packageset)
        #import epdb;epdb.st()
        self.group(packageset, plans=plans)
        import epdb;epdb.st()
        packageset = self.build(packageset, products=True)
        import epdb;epdb.st()
        self.display(packageset)


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

