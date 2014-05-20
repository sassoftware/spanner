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
import tempfile
from conary.lib import util


class ScmRepository(object):

    revision = None
    revIsExact = False

    def isLocal(self):
        """Returns True if the repository is on the local filesystem"""
        return False

    def getTip(self):
        """Return the latest commit ID for this repository"""
        raise NotImplementedError

    def updateCache(self):
        """Refresh the local cache for the repository"""
        raise NotImplementedError

    def getRecipe(self, subpath):
        """Return a dictionary of file contents at the given subpath"""
        assert self.revision
        # Update the local repository cache.
        workDir = tempfile.mkdtemp()
        try:
            prefix = self.checkout(workDir, subpath) or ''
            # Read in all the files for the requested subpath
            subDir = os.path.join(workDir, prefix, subpath)
            if not os.path.isdir(subDir):
                raise RuntimeError(
                        "sourceTree %s does not exist or is not a directory" %
                        subpath)
            files = {}
            for name in os.listdir(subDir):
                filePath = os.path.realpath(os.path.join(subDir, name))
                if not filePath.startswith(workDir):
                    raise RuntimeError(
                            "Illegal symlink %s points outside checkout: %s"
                            % (os.path.join(subpath, name), filePath))
                with open(filePath, 'rb') as fobj:
                    files[name] = fobj.read()
            return files
        finally:
            util.rmtree(workDir)

    def getAction(self, extra=''):
        """Return a Conary source action to unpack this repository"""
        raise NotImplementedError

    def fetchArchive(self, conarySource, snapPath):
        raise NotImplementedError

    def setFromTip(self):
        self.revision = self.getTip()
        self.revIsExact = True

    def getShortRev(self):
        if self.revIsExact:
            return self.revision[:12]
        else:
            return self.revision
