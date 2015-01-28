#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
'''
Main thread for spanner, provides high level actions for building 
conary packages from git repos
'''

import logging
import os
import time


from . import config
from . import fetcher
from . import reader
from . import checker
from . import builder
from . import grouper

logger = logging.getLogger(__name__)


class Worker(object):
    '''
    B{Worker}
    Main worker thread for spanner
    @param uri: uri locator for control repo
    @type uri: C{string}
    @keyword force: List of packages to build no matter what
    @keyword branch: branch of the repo
    @keyword cfgfile: use alternate cfg file
    @keyword test: Boolean to toggle debug mode (no builds)
    '''

    def __init__(self, uri, force=None, branch=None, cfgfile=None, 
                    group=False, products=False, test=False):

        self.uri = uri
        self.force = force or []
        self.cfgfile = cfgfile
        self.cfg = self.getDefaultConfig()
        self.group_build = group
        self.products_build = products
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
        '''return default config for spanner'''
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
        fetchPlans = fetcher.Fetcher(self.uri, self.cfg, self.branch)
        return fetchPlans.fetch()

    def read(self, path):
        '''
        pass in path to plans
        return set of package objects
        '''
        readPlans = reader.Reader(path, self.cfg)
        return readPlans.read()

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

    @classmethod 
    def display(cls, packageset):
        '''
        pass in set of package objects
        log built, groupname
        '''
        for secName, secPkgs in packageset.items():
            print "Section: %s\n" % secName
            for name, pkgs in secPkgs.items():
                print '\tBob Plan:\t%s' % name.split('bob-plans')[-1]
                for pkg in pkgs:
                    print '\tTroves:'
                    cpkgs = pkg.getTroveSpecs()
                    for cpkg in cpkgs:
                        print '\t\t\t%s' % cpkg.asString()
                    print '\tLog:\n\t\t\t%s\n' %  pkg.log


    def getPackageSet(self):
        '''return packageset and plans'''
        start = time.time()
        print "Begin gathering planpaths : %s" % start
        planpaths = self.fetch()
        end = time.time() - start
        print "End gathering planpaths : %s" % end
        start = time.time()
        print "Begin reading plans : %s" % start
        plans = self.read(planpaths)
        end = time.time() - start
        print "End reading plans : %s" % end
        start = time.time()
        print "Begin checking plans : %s" % start
        packageset = self.check(plans)
        end = time.time() - start
        print "End checking plans : %s" % end
        return packageset, plans

    def buildGroup(self, packageset=None, plans=None):
        '''build groups from packageset or control'''
        if not packageset or not plans:
            packageset, plans = self.getPackageSet()
        start = time.time()
        print "Begin cooking group : %s" % start
        self.group(packageset, plans=plans)
        end = time.time() - start
        print "End cooking group : %s" % end

    def buildProducts(self, packageset=None):
        '''build products from packageset or control'''
        if not packageset:
            packageset, dummy = self.getPackageSet()
        start = time.time()
        print "Begin building products : %s" % start
        packageset = self.build(packageset, products=True)
        end = time.time() - start
        print "End building products : %s" % end
        return packageset
         
    def main(self):
        '''Main function for Worker'''
        startStart = time.time()
        packageset, plans = self.getPackageSet()
        start = time.time()
        print "Begin building projects : %s" % start
        packageset = self.build(packageset)
        end = time.time() - start
        print "End building projects : %s" % end
        start = time.time()
        if self.group_build:
            self.buildGroup(packageset, plans)
        if self.products_build:
            packageset = self.buildProducts(packageset)
        self.display(packageset)
        end = time.time() - startStart
        print "Total time : %s" % end

if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

