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
Actions for reading plans
'''

import logging
import os
from collections import defaultdict


logger = logging.getLogger(__name__)


class Reader(object):
    '''
    B{Reader} -- Read plans from directory and return a set of plans
        - path path to plans
        - cfg cfg object
    @param path: path to the control repo snapshot
    @type path: string
    @param cfg: spanner cfg  
    @type: conary cfg object
    '''  

    def __init__(self, path, cfg):
        self.path = path
        self.cfg = cfg
        # Default data structure built from this list
        self.subdirs = [ self.cfg.projectsDir, 
                         self.cfg.productsDir,
                         self.cfg.externalDir,
                         self.cfg.commonDir,
                        ]

    def _get_plans(self):
        '''
        get the plans from the path and organize them into a structure
        '''
        logger.debug('Gathering plan files from %s' % self.path)
        plans = defaultdict(dict, dict([(x, set()) for x in self.subdirs]))

        for root, dummy, files in os.walk(self.path):
            for subdir in plans: 
                if os.path.basename(root) == subdir:
                    for fn in files:
                        if fn in self.cfg.fileNameBlackList:
                            continue
                        plans.setdefault(subdir, set()).add(
                                        os.path.join(root, fn))
        return plans


    def read(self):
        '''
        B{Read} 
        read the plans from the path and
        organize them into a structure
        @return: dict structure of plan paths
        @rtype: C{dict}
        '''
        return self._get_plans()


    def main(self):
        '''Main for Reader'''
        return self.read()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

