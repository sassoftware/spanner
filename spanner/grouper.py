import logging
import os
import time

from . import templates
from . import groups

logger = logging.getLogger(__name__)

class Grouper(object):

    def __init__(self, packageset, cfg=None, test=False, plans=None):
        self.packageset = packageset
        self._cfg = cfg
        if not self._cfg:
            self.getDefaultConfig()
        self.test = test

        if self._cfg.testOnly:
            logger.warn('testOnly set in config file ignoring commandline') 
            self.test = self._cfg.testOnly

        self.plans = plans

        self.projects = self.packageset.get(self._cfg.projectsDir)
        self.products = self.packageset.get(self._cfg.productsDir)
        self.external = self.packageset.get(self._cfg.externalDir)

    def buildGroup(self, groupname=None, external=None):
        # pkgs have to be formated into txt for the recipe template
        # either it is a comma seperated string of names 
        # or a string of names=version
        # TODO add code to handle no version
        from . import checker
    
        reader = checker.Checker()._read_plans
        
        assert self.plans

        common = self.plans.get(self._cfg.commonDir)

        fn = [ x for x in common if x.endswith(self._cfg.groupConfig) ]


        group_plan = self.reader(fn)

        import epdb;epdb.st()

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

        for name, pkgs in self.packages.items():
            # FIXME
            # Maybe overkill
            if name.endswith('-test'):
                continue
            for pkg in pkgs:
                # FIXME
                # Probably best idea
                if pkg.name.endswith('-test'):
                    continue
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

    def group(self):
        # TODO Finish buildGroup
        return self.buildGroup()

    def main(self):
        # TODO Finish buildGroup
        return self.buildGroup()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

