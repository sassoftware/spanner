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
Actions for fetching plans from control repos
'''

import logging
import os
import tempfile
from conary.lib import util as conary_util

import urllib
from . import config
from . import controller
from rev_file import RevisionFile

logger = logging.getLogger(__name__)

class Fetcher(object):
    '''
    B{Fetcher} Creates a snapshot of a control repo, 
                checks out plans, returns path to plans

        - path directory to snapshot the plans to
        - controller scm interaction supports  wms, git, local

    @param path: path to snapshot destination
    @type path: string
    @param controller: wms, git, or local 
    @type controller: controller object
    '''

    def __init__(self, uri, cfg, branch=None):
        self.uri = uri
        self.cfg = cfg
        self.branch = branch
        self.revision = None
        for localdir in [ self.cfg.planDir, self.cfg.cacheDir ]:
            conary_util.mkdirChain(localdir)
        self.path = tempfile.mkdtemp(dir=self.cfg.planDir)
        self.subtree = self.cfg.plansSubDir
        if self.is_local(uri):
            self.subtree = None
        self.fetched = False
        self.revision_file = RevisionFile()
        self.controller = self.initialize_controller(uri, self.branch)

    @classmethod
    def is_local(cls, uri):
        '''detect if uri is local'''
        return uri.startswith('/') or uri.startswith('file:')

    @classmethod
    def normalize_path(cls, uri):
        '''return absolute path of a uri'''
        if uri.startswith('./') or uri.startswith('../'):
            return os.path.abspath(uri) 
        return uri

    @staticmethod
    def _unquote(uri):
        '''replace : with / in a WMS uri'''
        return urllib.unquote(uri).replace(':', '/')

    def initialize_controller(self, uri, branch=None):
        '''
        Figure out from the uri string what type of controller 
        to use for fetching plans 
            - WMS
            - GIT
            - HG    -- Not Implemented 
            - LOCAL -- Not Implemented

        @param uri: uri to control repo
        @type uri: string
        '''
        ctrltype = 'GIT'
        uri = self.normalize_path(uri)
        paths = [ x for x in uri.split('/') ]
        base = '/'.join(paths[:3])
        path = '/'.join(paths[3:])
        rev = None
        if self.is_local(uri):
            ctrltype = 'LOCAL'
            raise NotImplementedError
        if base in (self.cfg.wmsBase, config.DEFAULT_WMS):
            base = self.cfg.wmsBase
            path = self._unquote(path.replace('api/repos/', ''))
            ctrltype = 'WMS'
            # If we find a tips or revision.txt we use that version 
            # Else we use the tip from rest api
            tip = self.revision_file.revs.get(path)
            if tip:
                rev = tip.get('id')
        # Silly but if we do not specify branch at command line 
        # then we assume it is already asssigned unless we can extract it 
        # from the end of a git uri
        if not branch:
            # TODO Use cfg option for this?
            branch = self.branch
            if len(path.split('?')) == 2:
                path, branch = path.split('?')
        return controller.Controller.create(ctrltype,
                                            base,
                                            path,
                                            branch,
                                            rev,
                                            )

    def _fetch(self):
        '''Fetch the plans from the repo'''
        logger.info('Fetching...')
        # FIXME If we use a temp file no need to create the dir
        #if not os.path.exists(self.path):
        #    logger.debug('Making directory for plans at %s' % self.path)
        #    os.makedirs(self.path)
        logger.info('Checking out sources from %s to %s' %
                    (self.uri, self.path))
        self.controller.snapshot(self.path, self.subtree)

    def fetch(self):
        '''
        Snapshot the control repo then fetch the plans from snapshot
        '''
        if not self.fetched:
            # TODO Add code to controller type 
            logger.info("Checking control source")
            check = self.controller.check()
            # TODO
            # One would think you would want to check self.fetched 
            # But probably safe to run fetch code again anyway
            if check:
                self._fetch()
                self.fetched = True
        return self.path

    def main(self):
        '''Main routine for Fetcher'''
        return self.fetch()


if __name__ == '__main__':
    import sys
    sys.excepthook = conary_util.genExcepthook()

