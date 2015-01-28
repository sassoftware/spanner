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
Actions for building bob-plans from WMS control.yaml
'''

import logging
import os
import tempfile
from conary.lib import util as conary_util

import urllib
from . import controller
from . import config
from rev_file import RevisionFile

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

    def __init__(self, uri, force=None, branch=None, cfgfile=None, test=False):

        self.uri = uri
        self.force = force or []
        self.cfgfile = cfgfile
        self.test = test
        self.branch = branch

        self.cfg = self.getDefaultConfig()
        if self.cfg.testOnly:
            logger.warn('testOnly set in config file ignoring commandline')
            self.test = self.cfg.testOnly

        self.tmpdir = self.cfg.tmpDir
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        assert os.path.exists(self.tmpdir)

    def getDefaultConfig(self, cfgFile=None):
        '''Get default config for spanner'''
        logger.info('Loading default cfg')
        if not cfgFile:
            cfgFile = self.cfgfile
        return config.SpannerConfiguration(config=cfgFile)

    def plan(self):
        '''Main call to create plans from repo'''
        plans = Planer(self.uri, self.cfg, self.branch)
        return plans.create()

class Planer(object):
    '''
    B{Planer} Create plans for a control repo, 
    @param uri: uri locator for control repo
    @type uri: C{string}
    @keyword force: List of packages to build no matter what 
    @keyword branch: branch of the repo
    '''

    def __init__(self, uri, cfg, branch=None):

        self.uri = uri
        self.cfg = cfg
        self.branch = branch
        self.revision = None
        for localdir in [ self.cfg.planDir, self.cfg.cacheDir ]:
            conary_util.mkdirChain(localdir)
        self.path = tempfile.mkdtemp(dir=self.cfg.planDir)
        self.subtree = self.cfg.plansSubDir
        if self.is_local(uri):
            self.subtree = None
        self.fetched = False
        self.revision_file = RevisionFile()
        self.controller = self.initialize_controller(uri, self.branch)

    @classmethod
    def is_local(cls, uri):
        '''detect if uri is local'''
        return uri.startswith('/') or uri.startswith('file:')

    @classmethod
    def normalize_path(cls, uri):
        '''return absolute path of a uri'''
        if uri.startswith('./') or uri.startswith('../'):
            return os.path.abspath(uri)
        return uri

    @staticmethod
    def _unquote(uri):
        '''replace : with / in a WMS uri'''
        return urllib.unquote(uri).replace(':', '/')

    def initialize_controller(self, uri, branch=None):
        '''
        Figure out from the uri string what type of controller
        to use for fetching plans
            - WMS
            - GIT
            - HG    -- Not Implemented
            - LOCAL -- Not Implemented

        @param uri: uri to control repo
        @type uri: string
        '''
        ctrltype = 'GIT'
        uri = self.normalize_path(uri)
        paths = [ x for x in uri.split('/') ]
        base = '/'.join(paths[:3])
        path = '/'.join(paths[3:])
        rev = None
        if self.is_local(uri):
            ctrltype = 'LOCAL'
            raise NotImplementedError
        if base == self.cfg.wmsBase:
            path = self._unquote(path.replace('api/repos/', ''))
            ctrltype = 'WMS'
            # If we find a tips or revision.txt we use that version 
            # Else we use the tip from rest api
            tip = self.revision_file.revs.get(path)
            if tip:
                rev = tip.get('id')
        # Silly but if we do not specify branch at command line 
        # then we assume it is already asssigned unless we can extract it 
        # from the end of a git uri
        if not branch:
            # TODO Use cfg option for this?
            branch = self.branch
            if len(path.split('?')) == 2:
                path, branch = path.split('?')
        return controller.Controller.create(ctrltype,
                                            base,
                                            path,
                                            branch,
                                            rev,
                                            )

    @staticmethod
    def _score(path):
        '''replace . or - with underscores'''
        return path.replace('.', '_').replace('-','_')

    @staticmethod
    def _dash(path):
        '''replace . with -'''
        return path.replace('.', '-')

    def _writePlan(self, filename, blob):
        '''write plan text (blob) to filename''' 
        path = os.path.join(self.path, filename)
        dirs = os.path.dirname(path)
        if dirs and not os.path.exists(dirs):
            os.makedirs(dirs)
        with open(path, 'a') as fobj:
            fobj.write(blob)

    def _makeDirs(self, path):
        '''make dir path'''
        path = os.path.join(self.path, path)
        if not os.path.exists(path):
            os.makedirs(path)

    def _create(self):
        '''Create plans'''
        logger.info('Creating plans for %s in %s' %
                                (self.uri, self.path))

        self._makeDirs(self.cfg.productsDir)
        self._makeDirs(self.cfg.externalDir)
        bfile = os.path.join(self.cfg.commonDir, 'branch.conf')
        self._writePlan(bfile, BRANCH.format(branch=self.branch))
        cfile = os.path.join(self.cfg.commonDir, 'common.conf')
        project = os.path.basename(self.controller.path)
        self._writePlan(cfile, COMMON.format(project=project))
        gfile = os.path.join(self.cfg.commonDir, 'group.conf')
        self._writePlan(gfile, GROUP.format(project=project))
        pfile = os.path.join(self.cfg.commonDir, 'platform.conf')
        self._writePlan(pfile, PLATFORM)
        revdata = self.controller.ctrl.parseRevisionsFromUri()
        for pkg, data in revdata.iteritems():
            name = self._score(data.get('name'))
            pkg =  'sasinside-' + self._dash(data.get('name'))
            #pathq = '/'.join(data.get('pathq').split(':')[:-1])
            pathq = data.get('path')
            filename = os.path.join(self.cfg.projectsDir, pkg + '.bob')
            template = BOBPLAN.format(pkgname=pkg, srctree=name, pathq=pathq)   
            self._writePlan(filename, template)



    def create(self):
        '''
        Create plans from revision.txt
        '''
        if not self.fetched:
            # TODO Add code to controller type 
            logger.info("Checking control source")
            check = self.controller.check()
            # TODO
            # One would think you would want to check self.fetched 
            # But probably safe to run fetch code again anyway
            if check:
                self._create()
                self.fetched = True
        return self.path

    def main(self):
        return self.create()


BOBPLAN = '''
includeConfigFile ../config/common.conf

scm {srctree} wms {pathq} %(branch)s

targetLabel %(ci_label)s

target []

target {pkgname}

[target:{pkgname}]
version %(version)s.%(scm)s
scm {srctree}
sourceTree {srctree} recipes/{pkgname}
flavor_set x86_64
'''

COMMON = '''
includeConfigFile platform.conf
includeConfigFile sources.conf
includeConfigFile branch.conf

shortenGroupFlavors True
resolveTrovesOnly True
showBuildLogs True

macros target_host <my.space.com>

macros project_name {project}

wmsBase http://wheresmystuff.unx.sas.com

macros master_label %(target_host)s@sas:%(project_name)s-%(branch)s

macros ci_short     %(project_name)s-ci

macros ci_host      %(ci_short)s-ci.cny.sas.com

macros ci_label     %(ci_host)s@sas:%(ci_short)s-%(branch)s-devel

macros target_label %(master_label)s


sourceLabel %(target_label)s

targetLabel %(target_label)s

'''

BRANCH = '''
macros branch {branch}
'''

GROUP = '''
includeConfigFile common.conf

macros groupTargetLabel %(target_label)s
macros groupName group-{project}-packages
macros includeExternal True

'''

PLATFORM = '''
includeConfigFile branch.conf
# CentOS 6n - Encapsulated with native Python

macros testbits_label   testbits.rb.rpath.com@rpath:centos-6n
macros testutils_label  newton.eng.rpath.com@rpath:centos-6n-testutils
macros distro_label     centos6.rpath.com@rpath:centos-6e
macros common_label     centos6.rpath.com@rpath:centos-6-common
macros contrib_label    contrib.rpath.org@rpath:centos-6e
macros contrib_py_label contrib.rpath.org@rpath:centos-6n
macros webunit_label    %(contrib_label)s
macros rndplat_devel_label    rndplat.cny.sas.com@sas:rndplat-%(branch)s-devel
macros rndplat_label    rndplat.cny.sas.com@sas:rndplat-%(branch)s

resolveTrovesOnly True

resolveTroves \\
    conary-testenv=testbits.rb.rpath.com@rpath:conary-common \\
    info-bin=conary.rpath.com@rpl:2 \\
    info-daemon=conary.rpath.com@rpl:2 \\
    info-rmake-chroot=conary.rpath.com@rpl:2 \\
    info-sys=conary.rpath.com@rpl:2 \\
    testutils=%(testutils_label)s \\
    mod_python=%(contrib_py_label)s \\
    python-webunit=%(contrib_py_label)s \\
    python-conary=%(common_label)s

resolveTroves group-rpath-packages=%(common_label)s

resolveTroves group-os=%(distro_label)s

autoLoadRecipes group-superclasses=%(common_label)s[is:x86_64]

rpmRequirements trove: rpm-rhel-6:lib(RPM-RHEL-6)

installLabelpath %(distro_label)s %(common_label)s %(testutils_label)s %(testbits_label)s %(rndplat_label)s

defaultBuildReqs []
'''



if __name__ == '__main__':
    import sys
    sys.excepthook = conary_util.genExcepthook()

