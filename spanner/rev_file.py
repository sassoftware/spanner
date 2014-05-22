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


class RevisionFile(object):

    def __init__(self):
        self.revs = {}
        self.basenames = {}
        self.filename = None

        self.parse()

    def parse(self):
        try:
            for line in open('tips'):
                _uri, _tip = line.split(' ', 1)
                self.revs[_uri] = {'id': _tip.strip()}
            self.filename = 'tips'
        except IOError:
            pass
        try:
            for line in open('revision.txt'):
                _uri, _branch, _tip = line.split(' ', 2)
                self.revs[_uri] = {'id': _tip.strip(), 'branch': _branch}
            self.filename = 'revision.txt'
        except IOError:
            pass

        for uri in self.revs:
            name = uri.replace('?', '#').split('#')[0]
            name = os.path.basename(name.rstrip('/'))
            if name.endswith('.git'):
                name = name[:-4]
            self.basenames[name] = uri

        if 'GERRIT_PROJECT' in os.environ:
            if not self.filename:
                raise RuntimeError("GERRIT_PROJECT is set but revision.txt "
                        "was not found in the workspace")
            project = os.path.basename(os.environ['GERRIT_PROJECT'])
            if project not in self.basenames:
                raise RuntimeError("GERRIT_PROJECT is set to %r but no repo "
                        "with that basename is in %s"
                        % (project, self.filename))
            uri = self.basenames[project]
            self.revs[uri] = {
                    'id': os.environ['GERRIT_PATCHSET_REVISION'],
                    'branch': os.environ['GERRIT_REFSPEC'],
                    'uri': self._gerrit_uri(),
                    'path': self._gerrit_path(),
                    }

    def _gerrit_uri(self):
        return '%s://%s:%s/%s' % (
                os.environ['GERRIT_SCHEME'],
                os.environ['GERRIT_HOST'],
                os.environ['GERRIT_PORT'],
                os.environ['GERRIT_PROJECT'],
                )

    def _gerrit_path(self):
        # This assumes that the name that the jenkins plugin gave to the gerrit
        # matches the silo name in WMS. In the future perhaps WMS can do
        # reverse mapping given a real git URL to find the virtual name.
        return '%s/%s' % (os.environ['GERRIT_NAME'], os.environ['GERRIT_PROJECT'])
