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
Package object
'''


import logging

from conary import trovetup
from conary import versions

logger = logging.getLogger(__name__)


class Package(object):
    '''
    B{Package}
    Package object
    '''

    __slots__ = ['name', 'target', 'label', 'repositories', 'controllers',
                 'buildLabel', 'targetLabel', 'sourceLabel',
                 'commit', 'branch', 'tag', 'allversions', 'latest',
                 'version', 'flavor', 'revision', 'uri', 'change',
                 'log', 'bobplan', 'next', 'scm',
                ]

    def __init__(self, **kwargs):
        for s in self.__slots__:
            setattr(self, s, kwargs.pop(s, None))

    def __repr__(self):
        return self.name

    def update(self, kwds):
        '''update key values'''
        for key, value in kwds.items():
            setattr(self, key, value)

    def get(self, flag):
        '''get key values'''
        return getattr(self, flag)

    def getTroveTuples(self):
        '''return list of trove tuples for package'''
        trovetupes = []
        if self.latest:
            for version, flavors in self.latest.iteritems():
                for flavor in flavors:
                    trovetupes.append(trovetup.TroveTuple((self.name, 
                                                            version, flavor)))
        else:
            if self.version:
                trovetupes.append(trovetup.TroveTuple((self.name, self.version, 
                                                                self.flavor)))
            else:
                if self.label:
                    ver = '/'.join(['', self.label.asString()])
                    version = versions.VersionFromString(ver)
                    trovetupes.append(trovetup.TroveTuple((self.name, version, 
                                                                self.flavor)))
        return trovetupes

    def getTroveSpecs(self):
        '''return list of trove specs for package'''
        trovespecs = []
        if self.latest:
            for version, flavors in self.latest.iteritems():
                for flavor in flavors:
                    trovespecs.append(trovetup.TroveSpec('%s=%s%s' % 
                                            (self.name, version, flavor)))
        else:
            if self.version:
                trovespecs.append(trovetup.TroveSpec('%s=%s%s' % (
                            self.name, self.version, self.flavor or '' )))
            else:
                if self.label:
                    version = '/'.join(['', self.label.asString()])
                    trovespecs.append(trovetup.TroveSpec('%s=%s%s' % (
                            self.name, version, self.flavor or '' )))
        return trovespecs

    @property
    def items(self):
        '''return a list of all slots'''
        return self.__slots__

if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()
