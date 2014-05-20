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

    def _get_plans(self):
        '''
        get the plans from the path and organize them into a structure
        '''
        logger.debug('Gathering plan files from %s' % self.path)
        plans = defaultdict(dict,{ 
                                'packages' : set(),
                                'common'   : set(),
                                'external' : set(),
                            }
                        )

        for root, dirs, files in os.walk(self.path):
            # don't add packages if self.plans is set
            if os.path.basename(root) == self.cfg.packagesDir:
                for fn in files:
                    plans.setdefault('packages', set()).add(
                        os.path.join(root, fn))
            if os.path.basename(root) == self.cfg.commonDir:
                for fn in files:
                    plans.setdefault('common', set()).add(
                        os.path.join(root, fn))
            if os.path.basename(root) == self.cfg.externalDir:
                for fn in files:
                    plans.setdefault('external', set()).add(
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

