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
Repository Object
'''

class Repo(object):
    '''
    B{Repo}
    Repository Object
    '''

    __slots__ = [   'name', 
                    'branch', 
                    'uri', 
                    'scm', 
                    'base', 
                    'path',
                    'silo',
                    'pathq',
                    'repos', 
                    'poll', 
                    'control', 
                    'wms', 
                    'locator',
                    'commit', 
                    'tags', 
                    'head', 
                    'revision', 
                    'change', 
                    'archive', 
                    'bobplan'
                ]

    def __init__(self, **kwargs):
        for s in self.__slots__:
            setattr(self, s, kwargs.pop(s, None))

    def __repr__(self):
        return self.name

    def update(self, kwds):
        '''update key values pairs'''
        for key, value in kwds.items():
            setattr(self, key, value)

    def get(self, flag):
        '''get key values pairs'''
        return getattr(self, flag)

    @property
    def items(self):
        '''returns a list of items'''
        return self.__slots__


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

