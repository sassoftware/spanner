import logging
import os
import time

from . import templates
from . import groups
from . import config

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

        self.plan = self.getGrpConfig(plans) 
        self.macros = self.plan.getMacros()
        self.version = time.strftime('%Y.%m.%d_%H%M.%S')
        self.projects = self.packageset[self._cfg.projectsDir]
        self.products = self.packageset[self._cfg.productsDir]
        self.external = self.packageset[self._cfg.externalDir]



    def getGrpConfig(self, plans):
        plan = config.BobConfig()
        if plans:
            common = plans.get(self._cfg.commonDir)
            if common:
                for path in common: 
                    if (path.endswith(self._cfg.groupConfig) 
                                    and os.path.isfile(path)):
                        plan.read(path)
        else:
            if self.test:
                from conary.build.macros import Macros
                macros = {  'groupName'       : 'group-foo-packages',
                            'includeExternal' : 'False',
                            'groupTargetLabel' : self._cfg.targetLabel or 'foo@foo:bar',
                        }
                #macros.update(self._cfg.macros)
                plan._macros = Macros(macros)
        return plan

    def _buildGroup(self, groupname=None, external=None):
        # pkgs have to be formated into txt for the recipe template
        # either it is a comma seperated string of names 
        # or a string of names=version
        # TODO add code to handle no version
    
        groupName = self.macros.get('groupName')

        if groupname and groupname.startswith('group-'):
            groupName = groupname

        groupLabel = self.macros.get('groupTargetLabel')

        pkgsList = []

        packages = self.projects

        if self.macros.get('includeExternal') or external:
            packages.update(self.external)

        for name, pkgs in packages.items():
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

        logger.debug('Building group for %s' % groupName)
        if self.test:
            logger.info('List of packages in group : %s' % str(pkgsList))
            template = templates.GroupTemplate( name=groupName,
                                            version=self.version,
                                            pkgs=pkgsList,
                                            label=groupLabel,
                                        )
            print template.getRecipe()
            return

        template = templates.GroupTemplate( name=groupName,
                                            version=self.version,
                                            pkgs=pkgsList,
                                            label=groupLabel,
                                        )
        
        import epdb;epdb.st()

        grp = groups.GroupBuilder(template)

        return grp.fricassee()      

    def group(self):
        # TODO Finish buildGroup
        return self._buildGroup()

    def main(self):
        # TODO Finish buildGroup
        return self._buildGroup()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

