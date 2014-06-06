#!/usr/bin/python


import sys
import os
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../../bob'))

from conary.lib import util
sys.excepthook = util.genExcepthook()


from spanner import worker

def main(uri, force=[], branch=None, cfgfile=None, test=False):
    wbee = worker.Worker(uri, force, branch=branch, cfgfile=cfgfile, test=test)
    wbee.main()


if __name__ == '__main__':
    sys.excepthook = util.genExcepthook()
      
    test0 = '/home/bsmith/git/scc/build-tools/build-tools/bob-plans' 
    test1 = 'file:///home/bsmith/git/scc/build-tools/build-tools/bob-plans'        
    test2 = 'ssh://git@scc.unx.sas.com/scc/build-tools?master'
    test3 = 'http://wheresmystuff.unx.sas.com/api/repos/scc/build-tools'
    test4 = '../../../build-tools/bob-plans?4' 
    
    force  = []
    branch = 'master'
    cfgfile = None
    test = True
    

    main(test3, force, branch, cfgfile, test)
