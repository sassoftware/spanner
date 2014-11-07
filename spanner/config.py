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


import os
import time

from conary.build.macros import Macros
from conary.conarycfg import CfgFlavor
from conary.lib import cfg
from conary.lib.cfgtypes import CfgList 
from conary.lib.cfgtypes import CfgString 
from conary.lib.cfgtypes import CfgDict
from conary.lib.cfgtypes import  CfgBool
from conary.lib.cfgtypes import ParseError
#from conary.lib.cfgtypes import CfgInt, CfgPathList, CfgQuotedLineList
from conary.lib.cfgtypes import CfgType
from conary.deps import deps
from bob import config as bobconfig


DEFAULT_PATH = ['/etc/spannerrc', '~/.spannerrc']


class CfgDependency(CfgType):

    def parseString(self, val):
        return deps.parseDep(val)

    def format(self, val, displayOptions=None):
        return str(val)


class PlanTargetSection(cfg.ConfigSection):
    '''
    Plan directory configuration:
    [plan:tmpwatch]
    scm git://gitlocation/repo
    '''

    scm                     = CfgString
    after                   = CfgList(CfgString)
    classVar                = CfgDict(CfgString)
    flavor_mask             = CfgFlavor
    flavor_set              = CfgString
    flavor                  = CfgList(CfgString)
    macros                  = CfgDict(CfgString)
    version                 = CfgString             # macros supported
    sourceTree              = CfgString
    serializeFlavors        = CfgBool
    noCommit                = CfgBool
    branch                  = CfgString

    _cfg_aliases            = [
        ('hg', 'scm'),
        ('git', 'scm'),
        ]



class MainConfig(cfg.SectionedConfigFile):
    '''
    Main Configuration for program
    '''
    targetLabel             = CfgString             # macros supported
    sourceLabel             = CfgString             # DEPRECATED (ignored)
    macros                  = CfgDict(CfgString)
    override                = CfgDict(CfgString)
    configPath              = CfgString
    scmType                 = CfgString
    scmUri                  = CfgString
    scmPlans                = CfgString
    bobUri                  = CfgString
    bobExec                 = CfgString
    logging                 = CfgBool
    logFile                 = CfgString
    lock                    = CfgString
    lockFile                = CfgString
    buildAll                = CfgBool

    branch                  = CfgString
    gitTarget               = CfgString

    # custom handling of sections
    _sectionMap = {'plans': PlanTargetSection}

    def __init__(self):
        cfg.SectionedConfigFile.__init__(self)
        self._macros = None


    def read(self, path, **kwargs):
        return cfg.SectionedConfigFile.read(self, path, **kwargs)

    def setSection(self, sectionName):
        if not self.hasSection(sectionName):
            found = False
            for name, cls in self._sectionMap.iteritems():
                if sectionName == name or sectionName.startswith(name + ':'):
                    found = True
                    self._addSection(sectionName, cls(self))
            if not found:
                raise ParseError('Unknown section "%s"' % sectionName)
        self._sectionName = sectionName
        return self._sections[sectionName]

    def getMacros(self):
        if self._macros is None:
            macros = Macros(self.macros)
            macros.update(self.override)
            macros['start_time'] = time.strftime('%Y%m%d_%H%M%S')
            macros['target_label'] = self.targetLabel % macros
            self._macros = macros
        return self._macros


class SpannerConfiguration(MainConfig):

    debugMode                   = (cfg.CfgBool, False)
    testOnly                    = (cfg.CfgBool, False)
    logFile                     = (cfg.CfgString, 'spanner.log')
    lockFile                    = (cfg.CfgString, 'spanner.lock')
    tmpDir                      = (cfg.CfgString, 'tmp')
    bobExec                     = (cfg.CfgString, '/usr/bin/bob')
    bobPlansUri                 = cfg.CfgString
    wmsBase                     = (cfg.CfgString, 'http://wheresmystuff.unx.sas.com')
    
    plansSubDir                 = (cfg.CfgString, 'bob-plans')
    projectsDir                 = (cfg.CfgString, 'projects')
    productsDir                 = (cfg.CfgString, 'products')
    externalDir                 = (cfg.CfgString, 'external')
    commonDir                   = (cfg.CfgString, 'config') # common
    commonFile                  = (cfg.CfgString, 'common.conf')
    groupConfig                 = (cfg.CfgString, 'group.conf')
    planDir                     = (cfg.CfgString, '_plan')
    cacheDir                    = (cfg.CfgString, '_cache')
    gitTarget                   = (cfg.CfgString, 'git-repo')
    fileNameBlackList           = (cfg.CfgList(cfg.CfgString), ['common.conf'])

    def __init__(self, config=None, readConfigFiles=False, ignoreErrors=False):
        super(SpannerConfiguration, self).__init__()
        self._config = config
        self.readConfigFiles = readConfigFiles
        self.ignoreErrors = ignoreErrors
        self._readCfg()

    def _readCfg(self, paths=[]):
        if self.readConfigFiles:
            paths = ['/etc/spannerrc', '~/.spannerrc']
        if self._config:
            paths.append(self._config)
        for path in paths:
            if path.startswith('~/') and 'HOME' in os.environ:
                path = os.path.join(os.environ['HOME'], path[2:])
            if os.path.isfile(path):
                self.read(path)


class BobConfig(bobconfig.BobConfig):

    def getTargets(self):
        macros = self.getMacros()
        return [x % macros for x in self.target]


def openPlan(path, preload=DEFAULT_PATH):
    plan = BobConfig()
    for item in preload:
        if item.startswith('~/') and 'HOME' in os.environ:
            item = os.path.join(os.environ['HOME'], item[2:])
        if os.path.isfile(item):
            plan.read(item)
    plan.read(path)
    return plan
