import logging
import os
import subprocess
import tempfile
import time
from collections import defaultdict

from ccfactory import ConaryClientFactory as _ccf
from . import config
from . import errors


logger = logging.getLogger(__name__)


class Builder(object):

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
        logger.info('Loading default cfg')
        self._cfg = config.SpannerConfiguration()
        self._cfg.read()


    def _getClient(self, force=False):
        if self._cclient is None or force:
            self._cclient = _ccf().getClient(
                model=False)
        return self._cclient

    conaryClient = property(_getClient)


    def _build(self, path, name=None, version=None, tag=None):
        '''
        @param path: A string representing the path 
                    to the bob plan to be executed
        @type path: String
        @param name: the name of package to be built. 
                required for setting version or tag (optional)
        @type name: String
        @param version: string representation of the commit 
                    from git repo (optional)
        @type version: String
        @param tag: string representation of tag from git repo (optional)
        @type: String
        '''
        cmd = [self.bobexec, path]

        if name and version:
            logger.info('Building package %s=%s' % (name, version))
            '''--set-version=conary="${Version}"'''
            logger.debug('Because of an ugly hack by W '
                         'we have to pass the macro for the name '
                         'bob-5 should fix this')
            #versionline = '--set-version=%s=%s' % (name, version)
            pkgmacro = '%(packageName)s'
            versionline = '--set-version=%s=%s' % (pkgmacro, version)
            cmd.append(versionline)
        if name and tag:
            logger.info('Building package %s with tag=%s' % (name, tag))
            '''--set-tag=conary="${Tag}"'''
            tagline = '--set-tag=%s=%s' % (name, tag)
            cmd.append(tagline)

        logger.debug('Calling bob\n%s' % ' '.join(cmd))
        if self.test:
            return 0, ' '.join(cmd)

        p = subprocess.Popen(cmd)
        p.communicate()
        return p.returncode, ' '.join(cmd)


    def updatePkgVersion(self, pkg):
        # Try and find conary versions
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

    def handler(self, pkgs):
        tobuild = set([])
        for name, pkg in pkgs.iteritems():
            for _p in pkg:
                if _p.change:
                    logger.info('%s has changed adding to build set' % _p.name)
                    tobuild.add(_p)
        return tobuild


    def build(self):
        packages = {}
        tobuild = self.handler(self.projects)
        built_packages = []
        failed_packages = []
        seen_plans = []
        skipped = []
        for pkg in tobuild:
            # lets not build pkgs more than once
            if pkg.bobplan not in seen_plans:
                seen_plans.append(pkg.bobplan)
            else:
                skipped.append(pkg.name)
                pkg.log = 'Built in %s' % pkg.bobplan
                packages.setdefault(pkg.name, set()).add(pkg)
                continue

            rc, cmd = self._build(  path = pkg.bobplan, 
                                    version=pkg.commit, 
                                    tag=pkg.tag,
                            )

            pkg.log = ('Failed: %s' if rc else 'Success: %s') % cmd
            if rc:
                failed_packages.append(pkg)
            else:
                pkg = self.updatePkgVersion(pkg)
                built_packages.append(pkg)
            packages.setdefault(pkg.name, set()).add(pkg)
        
        if self.test:
            for name, pkgs in packages.items():
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

    def main(self):
        # TODO Finish buildGroup
        return self.build()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

