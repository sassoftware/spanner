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
Actions for committing and cooking conary groups from template
'''

from . import factory
from conary import changelog
from conary.conaryclient import filetypes
from conary.build import cook
from conary.build import errors as builderrors

import logging

logger = logging.getLogger(__name__)


class GroupBuilder(object):
    '''
    B{GroupBuilder}
    Build a conary group from a template object
    @param template: a Template object
    '''

    def __init__(self, template):
        self.name = template.name
        self.version = template.version
        self.label = template.label
        self.recipe = template.getRecipe()
        self.spec = template.getTroveTuple()

    @classmethod       
    def commitGroupSource(cls, recipe=None, name=None, 
                                    version=None, label=None):
        '''
        B{groupSource}
        Commit group recipe to conary label
        @keyword recipe: String of a conary recipe
        @keyword label: conary label object
        ''' 
        cc = factory.ConaryClientFactory().getClient()
        logger.info("Creating %s:source=%s", name, str(label))
        message = "Automatic checkin for %s" % version
        message = message.rstrip() + "\n"
        cLog = changelog.ChangeLog(name = cc.cfg.name,
                contact = cc.cfg.contact, message = message)
        pathDict = {
                "%s.recipe" % name :
                    filetypes.RegularFile(contents=recipe, config=True),
                }
        cs = cc.createSourceTrove(name + ':source', str(label),
                version, pathDict, cLog)
        cc.getRepos().commitChangeSet(cs)

    @classmethod
    def cookGroup(cls, specs, buildlabel, macros=None):
        '''
        Cook group source on a conary label
        @param specs: list of trove specs
        @type  specs: list
        @keyword macros: dictionary of macros conary style
        @type macros: dict
        '''
        # sanitize macros
        macros = macros or {}

        # FIXME -- cfg might be trickier than this.
        # might need to build a cfg from bobplan
        cfg = factory.ConaryClientFactory().getCfg()
        cfg.buildLabel = buildlabel
        cfg.initializeFlavors()
        # END

        # Over configured... not necessary
        allowFlavorChange = 'allow-flavor-change' # Not False
        #targetFile = 'to-file' # Not sure how to use this yet
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
            cook.cookCommand(cfg, specs, prep=prep, macros=macros, 
                        resume=resume, allowUnknownFlags=unknownFlags, 
                        ignoreDeps=ignoreDeps, showBuildReqs=showBuildReqs, 
                        profile=profile, crossCompile=crossCompile, 
                        downloadOnly=downloadOnly, groupOptions=groupOptions,
                        )
        except builderrors.GroupFlavorChangedError, err:
            msg = ('\n(Add the --allow-flavor-change '
                            'flag to override this error)\n')
            err.args = (err.args[0] + msg)
            raise



    def fricassee(self):
        '''Automatically commit and cook conary group'''
        self.commitGroupSource(recipe=self.recipe, name=self.name, 
                                version=self.version, label=self.label)
        self.cookGroup(specs=[self.spec], buildlabel=self.label)
        return 
