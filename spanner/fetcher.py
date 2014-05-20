import logging
import os

logger = logging.getLogger(__name__)

class Fetcher(object):

    def __init__(self, path, controller, cfg):
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
        self.path = path
        self.controller = controller
        self.cfg = cfg
        self.fetched = False


    def _fetch(self):
        logger.info('Fetching...')
        if not os.path.exists(self.path):
            logger.debug('Making directory for plans at %s' % self.path)
            os.makedirs(self.path)
        logger.info('Checking out sources from %s to %s' %
                    (self.uri, self.path))
        self.controller.snapshot(self.path)

    def fetch(self):
        '''
        fetch snapshots control repo 
        '''
        if not self.fetched:
            # TODO Add code to controller type 
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

