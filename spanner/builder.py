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
Build actions for packages
'''

import logging
import os
import subprocess

from factory import ConaryClientFactory as _ccf
from . import config


logger = logging.getLogger(__name__)


class Builder(object):
    '''
    B{Builder}
    Build conary packages from the package objects
    @param packageset: Set of package objects to build
    @keyword cfg: cfg object
    @keyword test: toggle test run
    '''

    def __init__(self, packageset, cfg=None, test=False):
        self.packageset = packageset
        self._cfg = cfg
        if not self._cfg:
            self.getDefaultConfig()
        self.test = test

        if self._cfg.testOnly:
            logger.warn('testOnly set in config file ignoring commandline')
            self.test = self._cfg.testOnly

        self.bobexec = self._cfg.bobExec
        self.logfile = self._cfg.logFile
        self.tmpdir = self._cfg.tmpDir
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        assert os.path.exists(self.tmpdir)
        self.commonLabel = None
        self.projects = self.packageset[self._cfg.projectsDir]
        self.products = self.packageset[self._cfg.productsDir]
        self.external = self.packageset[self._cfg.externalDir]
        self._cclient = None

    def getDefaultConfig(self):
        '''get default cfg object for builder'''
        logger.info('Loading default cfg')
        self._cfg = config.SpannerConfiguration()
        self._cfg.read()


    def _get_client(self, force=False):
        '''return a fresh conary client'''
        if self._cclient is None or force:
            self._cclient = _ccf().getClient(
                model=False)
        return self._cclient

    conaryClient = property(_get_client)


    def _build(self, path, name=None, version=None, tag=None):
        '''
        Wrapper for bob the builder

        @param path: A string representing the path 
                    to the bob plan to be executed
        @type path: C{string}
        @param name: the name of package to be built. 
                required for setting version or tag (optional)
        @type name: C{string}
        @param version: string representation of the commit 
                    from git repo (optional)
        @type version: C{string}
        @param tag: string representation of tag from git repo (optional)
        @type: C{string}
        '''
        cmd = [self.bobexec, path]

        if name and version:
            logger.info('Building package %s=%s' % (name, version))
            '''--set-version=conary="${Version}"'''
            #logger.debug('Because of an ugly hack by W '
            #             'we have to pass the macro for the name '
            #             'bob-5 should fix this')
            #pkgmacro = '%(packageName)s'
            #versionline = '--set-version=%s=%s' % (pkgmacro, version)
            versionline = '--set-version=%s=%s' % (name, version)
            cmd.append(versionline)
        if name and tag:
            logger.info('Building package %s with tag=%s' % (name, tag))
            '''--set-tag=conary="${Tag}"'''
            tagline = '--set-tag=%s=%s' % (name, tag)
            cmd.append(tagline)

        logger.debug('Calling bob\n%s' % ' '.join(cmd))
        if self.test:
            return 0, ' '.join(cmd)

        proc = subprocess.Popen(cmd)
        proc.communicate()
        return proc.returncode, ' '.join(cmd)


    def updatePkgVersion(self, pkg):
        '''
        B{updatePkgVersion}
        Tries to find conary version of a package
        @param pkg: package object
        @return: updated package object
        '''
        revision = None
        version = None
        query = { pkg.target: { pkg.label: None, },}
        latest = self.conaryClient.repos.getTroveLeavesByLabel(query)
        if latest:
            logger.debug('Latest Version : %s' % str(latest))
            logger.debug('%s found on %s' % (pkg.target, pkg.label))
            versions = latest[pkg.target]
            version = max(versions)
            revision = version.trailingRevision().version
            logger.debug('Found revision %s of %s' % 
                            (str(revision),pkg.target))

            if version and revision:
                pkg.update({'revision': revision,
                            'version': version,
                            'latest': latest,
                            })
        return pkg

    def handler(self, packages):
        '''
        B{Handler} 
        checks to see if a package object 
        has change flag set true
        @param packages: set of package objects to be checked
        @return: a set of package objects to be built
        @rtype: C{set}
        '''
        tobuild = set([])
        for _, pkgs in packages.iteritems():
            for pkg in pkgs:
                if pkg.change:
                    logger.info('%s has changed adding to build set' % pkg.name)
                    tobuild.add(pkg)
        return tobuild


    def build(self, packages):
        '''
        B{Build}
 
        checks a set of package objects using handler
        then passes package objects to _build to be built
        @param packages: set of package objects
        @return: updated set of package objects
        @rtype: C{set}
        '''
        tobuild = self.handler(packages)
        built_packages = []
        failed_packages = []
        seen_plans = []
        skipped = []
        for name, pkgs in packages.items():
            for pkg in pkgs:
                if pkg in tobuild:
                    # lets not build pkgs more than once
                    if pkg.bobplan not in seen_plans:
                        seen_plans.append(pkg.bobplan)
                    else:
                        skipped.append(pkg.name)
                        pkg.log = 'Built in %s' % pkg.bobplan
                        pkg = self.updatePkgVersion(pkg)
                        packages.setdefault(pkg.name, set()).add(pkg)
                        continue
                    # FIXME
                    # For now this is the version convention
                    # TODO 
                    # Add revision.txt  info to trove source metadata
                    version = None
                    if pkg.commit:
                        version = '%s.%s' % (pkg.branch, pkg.commit[:12])
                    rc, cmd = self._build(  path=pkg.bobplan, 
                                            name=pkg.name,
                                            version=version, 
                                            tag=pkg.tag,
                                    )

                    pkg.log = ('Failed: %s' if rc else 'Success: %s') % cmd
                    if rc:
                        failed_packages.append(pkg)
                    else:
                        pkg = self.updatePkgVersion(pkg)
                        built_packages.append(pkg)
                packages.setdefault(name, set()).add(pkg)
        
        if self.test:
            for _, pkgs in packages.items():
                for pkg in pkgs:
                    logger.info('%s  :  %s\n' % (pkg.name, pkg.log))
            logger.info('List of plans built: %s' % seen_plans)
            logger.info('List of skipped packages: %s' % skipped)

        logger.info('List of packages built: %s' %
                    [pkg.name for pkg in built_packages])

        if failed_packages:
            logger.warn('List of failed package builds: %s' %
                        [pkg.name for pkg in failed_packages])

        return packages

    def buildProjects(self):
        '''
        Build Projects from the packageset
        '''
        # TODO Finish buildGroup
        projects = self.build(self.projects)
        self.packageset[self._cfg.projectsDir].update(projects)
        return self.packageset

    def buildProducts(self):
        '''
        Build Products from the packageset
        '''
        products = self.build(self.products)
        self.packageset[self._cfg.productsDir].update(products)
        return self.packageset

    def main(self):
        '''Main routine for C{Builder}'''
        return self.buildProjects()

if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

