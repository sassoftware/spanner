import logging
import os
import time

from . import templates
from . import groups

logger = logging.getLogger(__name__)

class Grouper(object):

    def __init__(self, uri, branch, cache=None, cfg=None, test=False,
                 plans=None):
        self.uri = uri
        self.cachedir = cache
        self.branch = branch
        self.identifier = '_'.join([self.branch, 
                                    time.strftime('%Y.%m.%d_%H%M.%S')])
        self.prepped = False
        self.fetched = False
        self._cclient = None
        self._cfg = cfg
        if not self._cfg:
            self.getDefaultConfig()
        if not self.cachedir:
            self.cachedir = self._cfg.cacheDir
        self.debug = self._cfg.debugMode
        self.test = test
        self.head = None
        self.plans = plans
        if self.plans:
            self.plans = [os.path.basename(plan) for plan in self.plans]

        if self._cfg.testOnly:
            logger.warn('testOnly set in config file ignoring commandline')
            self.test = self._cfg.testOnly
        self.bobexec = self._cfg.bobExec
        self.logfile = self._cfg.logFile
        self.tmpdir = self._cfg.tmpDir
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        assert os.path.exists(self.tmpdir)
        self.plandir = os.path.join(self.tmpdir, 'plans')
        self.commonDir = self._cfg.commonDir
        self.commonFile = self._cfg.commonFile
        self.packagesDir = self._cfg.packagesDir
        self.force_build = []
        self.commonLabel = None

    def buildGroup(self, packages, groupname=None, external=None):
        # pkgs have to be formated into txt for the recipe template
        # either it is a comma seperated string of names 
        # or a string of names=version
        # TODO add code to handle no version
        
        if not self.plans:
            self.prep()
            if self.fetched:
                self.plans = self.gather_plans()
       
        fn = [ x for x in self.plans['common'] 
                            if x.endswith(self._cfg.groupConfig) ][0]

        group_plan = self.read_plan(fn)

        macros = group_plan.getMacros()

        if macros.get('includeExternal') or external:
            external_plans = self.plans['external']
            if external_plans:
                external_packages = self.gather_packages(external_plans)
        
        groupName = macros.get('groupName', 'group-foobar')

        if groupname and groupname.startswith('group-'):
            groupName = groupname

        groupLabel = group_plan.getTargetLabel()

        pkgsList = []

        for name, pkgs in packages.items():
            for pkg in pkgs:
                if pkg.version:
                    pkgsList.append('%s=%s' % (pkg.name, str(pkg.version)))
                else:
                    pkgsList.append('%s' % (pkg.name))

        if external_packages:
            for name, pkgs in external_packages.items():
                for pkg in pkgs:
                    pkgsList.append('%s=%s' % (pkg.name, str(pkg.version)))

        logger.debug('Building group for %s' % groupName)
        if self.test:
            logger.info('List of packages in group : %s' % str(pkgsList))
            return

        template = templates.GroupTemplate( name=groupName,
                                            version=self.identifier,
                                            pkgs=pkgsList,
                                            label=groupLabel,
                                        )

        grp = groups.GroupBuilder(template)

        return grp.fricassee()      

    def main(self):
        # TODO Finish buildGroup
        return self.buildGroup()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

