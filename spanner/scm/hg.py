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
Helper functions for dealing with mercurial (hg) repositories.
'''

import logging
import os
import subprocess
from .. import scm

from mercurial import hg, ui
from mercurial.node import short


log = logging.getLogger(__name__)


class HgRepository(scm.ScmRepository):

    def __init__(self, uri, branch, cache='_cache'):
        self.uri = uri
        self.branch = branch
        dirPath = self.uri.split('//', 1)[-1]
        dirPath = dirPath.replace('/', '_')
        self.repoDir = os.path.join(cache, dirPath, 'hg')

    def isLocal(self):
        return self.uri.startswith('/') or self.uri.startswith('file:')

    def getTip(self):
        hg_ui = ui.ui()
        if hasattr(hg, 'peer'):
            repo = hg.peer(hg_ui, {}, self.uri)
        else:
            repo = hg.repository(hg_ui, self.uri)
        return short(repo.heads()[0])

    def updateCache(self):
        # Create the cache repo if needed.
        if not os.path.isdir(self.repoDir):
            os.makedirs(self.repoDir)
        if not os.path.isdir(self.repoDir + '/.hg'):
            subprocess.check_call(['hg', 'init'], cwd=self.repoDir)
        subprocess.check_call(['hg', 'pull', '-qf', self.uri], cwd=self.repoDir)

    def snapshot(self, workDir, subtree):
        subprocess.check_call(['hg', 'archive', '--type=files',
            '--rev', self.revision, '--include', subtree,
            workDir], cwd=self.repoDir)

    def getAction(self, extra=''):
        return 'addMercurialSnapshot(%r, tag=%r%s)' % (self.uri,
                self.getShortRev(), extra)
