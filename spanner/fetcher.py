import logging
import os
import tempfile
from conary.lib import util as conary_util

from . import controller
from rev_file import RevisionFile

logger = logging.getLogger(__name__)

class Fetcher(object):

    def __init__(self, uri, cfg, branch=None):
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
        self.rf = RevisionFile()
        self.controller = self.initialize_controller(uri, self.branch)

    def is_local(self, uri):
        return uri.startswith('/') or uri.startswith('file:')

    def normalize_path(self, uri):
        if uri.startswith('./') or uri.startswith('../'):
            return os.path.abspath(uri) 
        return uri


    def initialize_controller(self, uri, branch=None):
        ctrltype = 'GIT'
        uri = self.normalize_path(uri)
        paths = [ x for x in uri.split('/') ]
        base = '/'.join(paths[:3])
        path = '/'.join(paths[3:])
        rev = None
        if self.is_local(uri):
            ctrltype = 'LOCAL'
        if base == self.cfg.wmsBase:
            path = path.replace('api/repos/', '')
            ctrltype = 'WMS'
            # If we find a tips or revision.txt we use that version 
            # Else we use the tip from rest api
            tip = self.rf.revs.get(path)
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
        fetch snapshots control repo 
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
        return self.fetch()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

