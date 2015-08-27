#!/usr/bin/python


import sys
import os
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../../bob'))

from conary.lib import util
sys.excepthook = util.genExcepthook()


from spanner import worker
from spanner import planer


def main(uri, force=[], branch=None, cfgfile=None, test=False):
    wbee = worker.Worker(uri, force, branch=branch, cfgfile=cfgfile, test=test)
    wbee.main()

def create(uri, force=[], branch=None, cfgfile=None, test=False):
    wbee = planer.Worker(uri, force, branch=branch, cfgfile=cfgfile, test=test)
    wbee.plan()

if __name__ == '__main__':
    sys.excepthook = util.genExcepthook()

    test0 = '/home/bsmith/git/gerrit-pdt/tools/build-tools/build-tools/bob-plans'
    test1 = 'file:///home/bsmith/git/gerrit-pdt/tools/build-tools/build-tools/bob-plans'
    test2 = 'ssh://gerrit-pdt.unx.sas.com/gerrit-pdt/tools/build-tools?master'
    test3 = 'http://wheresmystuff.unx.sas.com/api/repos/gerrit-pdt/tools:build-tools'
    test4 = '../../../build-tools/bob-plans?4'
    test5 = 'http://wheresmystuff.unx.sas.com/api/repos/gitgrid/VirtualApplications:Content:ams-vapp'

    force  = []
    #branch = 'master'
    branch = '5'
    cfgfile = None
    test = True
    

    #main(test3, force, branch, cfgfile, test)
    create(test5,force, branch, cfgfile, test)

