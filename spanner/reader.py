import logging
import os
from collections import defaultdict


logger = logging.getLogger(__name__)


class Reader(object):

    def __init__(self, path, cfg):
        '''
        B{Reader} -- Read plans from directory and return a set of plans
            - path path to plans
            - cfg cfg object
        @param path: path to the control repo snapshot
        @type path: string
        @param cfg: spanner cfg  
        @type: conary cfg object
        '''  
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

        for root, dirs, files in os.walk(self.path):
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
        Read plans from directory
        @return data structure of plan paths
        read the plans from the path
        organize them into a structure
        '''
        return self._get_plans()


    def main(self):
        # TODO Finish buildGroup
        return self.read()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

