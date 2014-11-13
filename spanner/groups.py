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

from . import factory
from conary import changelog
from conary.conaryclient import filetypes
from conary.build import cook
from conary.build import errors as builderrors

import logging

logger = logging.getLogger(__name__)


class GroupBuilder(object):

    def __init__(self, template):
        self.name = template.name
        self.version = template.version
        self.label = template.label
        self.recipe = template.getRecipe()
        self.spec = template.getTroveTuple()
        self._cclient = None
        self._cfg = None

    conaryClientFactory = factory.ConaryClientFactory

    def _getClient(self, force=False):
        if self._cclient is None or force:
            self._cclient = self.conaryClientFactory().getClient(
                model=False)
        return self._cclient

    conaryClient = property(_getClient)

    def _getCfg(self, force=False):
        if self._cfg is None or force:
            self._cfg = self.conaryClientFactory().getCfg()
        return self._cfg

    conaryCfg = property(_getCfg)

        
    def groupSource(self, recipe=None, label=None):
        cc = self.conaryClient
        troveName = str(self.name)
        version = str(self.version)
        if not label:
            label = self.label
        groupRecipeContents = recipe
        if not groupRecipeContents:
            groupRecipeContents = self.createRecipe()
        logger.info("Creating %s:source=%s", troveName, str(label))
        message = "Automatic checkin for %s" % version
        message = message.rstrip() + "\n"
        cLog = changelog.ChangeLog(name = cc.cfg.name,
                contact = cc.cfg.contact, message = message)
        pathDict = {
                "%s.recipe" % troveName :
                    filetypes.RegularFile(contents=groupRecipeContents, config=True),
                }
        cs = cc.createSourceTrove(troveName + ':source', str(label),
                version, pathDict, cLog)
        cc.getRepos().commitChangeSet(cs)

    def cookGroup(self, specs, macros={}):
        '''
        @param specs list of trove specs
        @type  specs list
        @param macros dictionary of macros conary style
        @type  macros dict
        '''
        # FIXME -- cfg might be trickier than this.
        # might need to build a cfg from bobplan
        cfg = self.conaryCfg
        cfg.buildLabel = self.label
        cfg.initializeFlavors()
        # END

        # Over configured... not necessary
        allowFlavorChange = 'allow-flavor-change' # Not False
        targetFile = 'to-file' # Not sure how to use this yet
        crossCompile = None # 'cross'
        unknownFlags = None # 'unknown-flags'
        profile = False
        downloadOnly = False
        resume = None
        downloadOnly = False
        resume = None
        showBuildReqs = False
        ignoreDeps = False
        prep = None

        # Hilarious over programing
        groupOptions = cook.GroupCookOptions(alwaysBumpCount=True,
                                 errorOnFlavorChange=allowFlavorChange,
                                 shortenFlavors=cfg.shortenGroupFlavors) 

        try:
            cook.cookCommand(cfg, specs, prep=prep, macros=macros, resume=resume,
                         allowUnknownFlags=unknownFlags, ignoreDeps=ignoreDeps,
                         showBuildReqs=showBuildReqs, profile=profile,
                         crossCompile=crossCompile, downloadOnly=downloadOnly,
                         groupOptions=groupOptions,
                         )
        except builderrors.GroupFlavorChangedError, err:
            err.args = (err.args[0] +
                        '\n(Add the --allow-flavor-change flag to override this error)\n',)
            raise



    def fricassee(self):
        self.groupSource(self.recipe, self.label)
        self.cookGroup([self.spec])
        return 
