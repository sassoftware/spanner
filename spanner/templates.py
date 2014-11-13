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


import logging
import string

from conary import trovetup
from conary import versions

logger = logging.getLogger(__name__)

DEFAULT_RECIPE_TEMPLATE = """
class {0}(GroupSetRecipe):
    name = '{1}'
    version = '{2}'

    def setup(r):
        r.dumpAll()

        local = r.Repository(r.cfg.buildLabel, r.flavor)

        pkgs = local.latestPackages()

        r.Group(pkgs, checkPathConflicts=False, scripts=None)

"""


GROUP_RECIPE_TEMPLATE = """
class {0}(GroupSetRecipe):
    name = '{1}'
    version = '{2}'

    def setup(r):
        r.dumpAll()

        local = r.Repository(r.cfg.buildLabel, r.flavor)

        pkgs = local.find(
                {3}
                )

        r.Group(pkgs, checkPathConflicts=False, scripts=None)

"""


class GroupTemplate(object):
    __slots__ = ['name', 'version', 'flavor', 'label', 'pkgs', 'recipe', 'spec']

    def __init__(self, **kwargs):
        for s in self.__slots__:
            setattr(self, s, kwargs.pop(s, None))

    def get(self, flag):
        return getattr(self, flag)

    def createRecipe(self):
        className = ''.join([string.capwords(x) for x 
                                in self.name.split('-')])
        if self.pkgs:
            pkgs = [ "'%s'" % x for x in self.pkgs]
            pkgString = ',\n\t\t'.join(pkgs)
            return  GROUP_RECIPE_TEMPLATE.format(className, 
                                    self.name, self.version, pkgString)

        return  DEFAULT_RECIPE_TEMPLATE.format(className, 
                                    self.name, self.version)

    def getRecipe(self):
        if not self.recipe:
            self.recipe = self.createRecipe()
        return self.recipe

    def getSpec(self):
        if not self.spec:
            self.spec = "%s=%s" % (self.name, self.label)
        return self.spec

    def getTroveTuple(self):
        version = self.label
        if version:
            if not version.startswith('/'):
                version = '/'.join(['', version])
            version = versions.VersionFromString(version)
        return trovetup.TroveTuple((self.name, version, self.flavor))

    def getTroveSpec(self):
        version = self.label
        if version:
            if not version.startswith('/'):
                version = '/'.join(['', version])
            version = versions.VersionFromString(version)
        return trovetup.TroveSpec.fromString('%s=%s' % (self.name, 
                                                version.asString()))

    def getTroveTuples(self):
        trovetupes = []
        if self.pkgs:
            for pkg in self.pkgs:
                trvSpec = trovetup.TroveSpec.fromString(pkg)
                _n = trvSpec.name
                version = trvSpec.version
                if not trvSpec.version.startswith('/'):
                    version = '/'.join(['', trvSpec.version])
                _v = versions.VersionFromString(version)
                # TODO
                # FIXME This needs to be an actual conary Flavor
                _f = trvSpec.flavor
                trovetupes.append(trovetup.TroveTuple((_n, _v, _f)))
        return trovetupes

    def getTroveSpecs(self):
        trovespecs = []
        if self.pkgs:
            for pkg in self.pkgs:
                trvSpec = trovetup.TroveSpec.fromString(pkg)
                _n = trvSpec.name
                version = trvSpec.version
                if not trvSpec.version.startswith('/'):
                    version = '/'.join(['', trvSpec.version])
                version = versions.VersionFromString(version)
                _v = version.asString()
                # TODO 
                # Add flavor support
                trovespecs.append(trovetup.TroveSpec.fromString(('%s=%s' % (_n,_v))))
        return trovespecs

    @property
    def items(self):
        return self.__slots__




