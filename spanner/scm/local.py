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
Helper functions for dealing with local (bare files) repositories.
'''

import logging
import os
import subprocess
from conary.lib import util as conary_util
from .. import scm


log = logging.getLogger(__name__)


class LocalRepository(scm.ScmRepository):

    def __init__(self, uri, branch, cache='_cache'):
        self.uri = uri
        self.branch = branch
        dirPath = self.uri.split('//', 1)[-1]
        dirPath = dirPath.replace('/', '_')
        self.repoDir = os.path.join(cache, dirPath, 'local')
        conary_util.mkdirChain(self.repoDir)


    def isLocal(self):
        return self.uri.startswith('/') or self.uri.startswith('file:')

    def normalizePath(self):
        if self.uri.startswith('./') or self.uri.startswith('../'):
            return os.path.abspath(self.uri)
        return self.uri

    def getTip(self):
        pass

    def updateCache(self):
        pass

    def snapshot(self, workDir, subtree=None):
        '''
        workDir is directory to copy to
        subtree is directory inside the path to the files...
        '''
        path = self.uri
        if subtree:
            path = os.path.join(self.uri, subtree)
        p1 = subprocess.Popen(['tar', '-c', '-C', path, '.'],
                                stdout=subprocess.PIPE, 
                                cwd=self.repoDir)

        p2 = subprocess.Popen(['tar', '-x'], stdin=p1.stdout, cwd=workDir)
        p1.stdout.close()  # remove ourselves from between tar and tar
        p1.wait()
        p2.wait()
        if p1.returncode:
            raise RuntimeError("tar exited with status %s" % p1.returncode)
        if p2.returncode:
            raise RuntimeError("tar exited with status %s" % p1.returncode)


    def getAction(self, extra=''):
        return 'addLocalSnapshot(%r, tag=%r%s)' % (self.uri,
                self.getShortRev(), extra)
