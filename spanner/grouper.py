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
Actions for building groups
'''

import logging
import os
import time

from . import templates
from . import groups
from . import config
from . import factory

from conary import display
from conary.conaryclient.cmdline import parseTroveSpec

logger = logging.getLogger(__name__)

class Grouper(object):
    '''
    B{Grouper}
    Build groups from set of packages
    @param packageset: dict of { sections : packages }
    @type packageset: C{string}
    @keyword cfg: alternate cfg object
    @keyword test: Boolean to toggle debuging
    @keyword plans: Plan object from C{Worker} read()
    '''


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

    def getDefaultConfig(self):
        '''get default cfg object for grouper'''
        logger.info('Loading default cfg')
        self._cfg = config.SpannerConfiguration(readConfigFiles=True)
        self._cfg.read()

    def getGrpConfig(self, plans):
        '''
        B{getGrpConfig}
        iter plan objects and find match for group config file
        @param plans: set of plans from C{Worker} read()
        @return: plan object
        '''
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
                            'groupTargetLabel' : self._cfg.targetLabel or 'foo@f:bar',
                        }
                #macros.update(self._cfg.macros)
                plan._macros = Macros(macros)
        plan.wmsBase = self._cfg.wmsBase
        return plan

    @classmethod
    def _get_conary_pkg(cls, trvspec):
        '''Find latest conary version of a trove spec'''
        latest = None
        # Try and find conary versions 
        cc = factory.ConaryClientFactory().getClient()
        ss = cc.getSearchSource(flavor=0)
        if isinstance(trvspec, str):
            trvspec = parseTroveSpec(trvspec)
        matches = ss.findTroves([trvspec], bestFlavor=False, allowMissing=True)
        # Parse trvspec and fetch that trove
        if matches:
            latest = max(matches[trvspec])
        return latest

    @classmethod
    def _find_group_troves(cls, topLevelGroups):
        '''
        Find all the troves in a conary top level group
        @param topLevelGroups: list of top level groups 
        @type topLevelGroups: C{string}
        @return: dict of troves
        @rtype: dict
        '''
        interestingTroves = {}
        cc = factory.ConaryClientFactory().getClient()
        ss = cc.getSearchSource(flavor=0)
        for troveTup, troveObj, flags, indent in display.iterTroveList(
                                                ss, topLevelGroups,
                                                recurseAll = True,
                                                recursePackages = True,
                                                showNotByDefault = True,
                                                showNotExists = True):
            name, version, flavor = troveTup
            if ':' not in name and not name.startswith('group-'):
                interestingTroves.setdefault(troveTup.name, []).append(troveTup)
        return interestingTroves

    def _get_group_versions(self, trvspec=None):
        '''
        Find version of a conary group
        @keyword trvspec: Set a specific group to look up
        @return: dict of { name : troveTup }
        '''
        grpTroves = {}
        if not trvspec:    
            trvspec = self._default_grp_trvspec()
        grp = self._get_conary_pkg(trvspec)
        if grp:
            grpTroves.update(self._find_group_troves([grp]))
        return grpTroves

    def _default_grp_trvspec(self):
        '''Return default group trovespec fromg cfg'''
        group = self.macros.get('groupName')
        label = self.macros.get('groupTargetLabel')
        label %= self.macros
        return parseTroveSpec('%s=%s' % (group, label))

    def _latest_default_grp(self):
        '''Return latest group trovespec from cfg'''
        return self._get_conary_pkg(self._default_grp_trvspec())

    def _buildGroup(self, trvspec=None, external=False):
        '''
        pkgs have to be formated into txt for the recipe template
        either it is a comma seperated string of names 
        or a string of names=version
        @todo: add code to handle no version
        '''

        pkgsList = []

        packages = self.projects

        if self.macros.get('includeExternal') or external:
            packages.update(self.external)

        if not trvspec:
            trvspec = self._default_grp_trvspec()
            label = trvspec.version
            if '/' in label:
                label = label.split('/')[-2]

        grpVersions = self._get_group_versions(trvspec)

        changed = False

        for name, pkgs in packages.items():
            # FIXME
            # Maybe overkill
            for pkg in pkgs:
                # FIXME
                # Probably best idea
                if pkg.name.endswith('-test'):
                    continue
                if pkg.version:
                    grpvers = grpVersions.get(pkg.name)
                    if grpvers:
                        grpver = max(grpvers)    
                        if pkg.version != grpver.version:
                            changed = True
                    else:
                        changed = True
 
                    pkgsList.append('%s=%s' % (pkg.name, str(pkg.version)))
                else:
                    pkgsList.append('%s' % (pkg.name))

        template = templates.GroupTemplate( name=trvspec.name,
                                            version=self.version,
                                            pkgs=pkgsList,
                                            label=label,
                                        )

        if self.test or not changed:
            logger.info('Skipping group build...')
            logger.info('List of packages in group : %s' % str(pkgsList))
            if self.test:
                print template.getRecipe()
            return

        logger.debug('Building group for %s' % trvspec.name)
        
        grp = groups.GroupBuilder(template)

        return grp.fricassee()      
        

    def group(self):
        '''Build a conary group from a packageset''' 
        # TODO Finish buildGroup
        current = self._latest_default_grp()
        if current:
            logger.debug('Current Group Version : %s' % current.asString())
        self._buildGroup()
        latest = self._latest_default_grp()
        if latest != current:
            logger.info('Updated Group Version : %s' % latest.asString())
        return 

    def main(self):
        '''Main function for Grouper'''
        # TODO Finish buildGroup
        return self._buildGroup()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

