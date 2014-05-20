#!/usr/bin/python2.6
#
#
# Copyright (c) SAS Institute Inc.
#
# All rights reserved.
#



import os
import urlparse
from conary import conarycfg
from conary import conaryclient
from conary.conaryclient import cmdline
from conary.conaryclient.cmdline import parseTroveSpec

from conary.deps import deps
from conary.repository.errors import TroveMissing



class BaseUtil(object):
    
    def main(self):
        pass

         

class BaseFileUtil(BaseUtil):

    def __init__(self, uri):
        self.uri = uri        

    def isRemote(self, uri=None):
        if not uri:
            uri = self.uri
        remote_repo_prefix = ['http://', 'https://', 'git://', 'ssh://']
        for pre in remote_repo_prefix:
            if uri.startswith(pre):
                return True
        assert os.path.exists(uri)
        return False

    def genDirPath(self, uri, subdir):
        url = urlparse.urlparse(uri)
        repo = os.path.basename(url.path).replace('.git','')
        path = os.path.join(url.netloc, repo)
        if subdir:
            path = os.path.join(subdir, path)
        if path.startswith('~/') and 'HOME' in os.environ:
            path = os.path.join(os.environ['HOME'], path[2:])
        else:
            path = os.path.join(os.getcwd(), path)
        return path
  

class BaseConaryUtil(BaseUtil):
    
    def __init__(self):
    
        self._ccfg = conarycfg.ConaryConfiguration(True)
        self._cclient = conaryclient.ConaryClient(self._ccfg)
        self._repos = self._cclient.getRepos()

 
 

class BuildReqs(BaseConaryUtil):
    
    """
    Print all buildRequires referenced by the specified (binary) trove.
    """

    def __init__(self, trovespecs):
        super(BuildReqs, self).__init__()
        self.main(trovespecs)

    def main(self, troveSpecs):
        for troveSpec in troveSpecs:
            # Parse cmdline arguments and fetch that trove
            name, version, flavor = parseTroveSpec(troveSpec)
            matches = self._repos.findTrove(None, (name, version, flavor))
            troveTup = max(matches)
            trv = self._repos.getTrove(withFiles=False, *troveTup)

            tups = set()
            for req in trv.getTroveInfo().buildReqs.iter():
                tups.add((req.name(), req.version(), req.flavor()))

            for tup in sorted(tups):
                print '%s=%s[%s]' % tup
    


class Tracepath(BaseConaryUtil):

    """
    Tracepath of a given trove
    """

    def __init__(self, trovespecs):
        super(Tracepath, self).__init__()
        self.main(trovespecs)

    def resolve(self, names, version, ilp=None):
        if isinstance(names, str):
            single = True
            names = [names]
        else:
            single = False

        query = [(name, version, None) for name in names]
        results = self._repos.findTroves(ilp, query, bestFlavor=False)
        ret = []
        for name in names:
            troves = results[(name, version, None)]
            v = max(x[1] for x in troves)
            nvf = [x for x in troves if x[1] == v][0]
            ret.append(nvf)

        if single:
            return ret[0]
        else:
            return ret


    def main(self, troveSpecs):
        for troveSpec in troveSpecs:
            print troveSpec
            print '-' * 20
            name, version, _ = cmdline.parseTroveSpec(troveSpec)
            n, v, f = self.resolve(name, version)
            print 'Selected %s=%s' % (n, v)
            seen = set()
            while v:
                try:
                    trv = self._repos.getTrove(n, v, f)
                except TroveMissing:
                    if n.endswith(':source') and v.hasParentVersion():
                        # rMake builds binaries as if they were shadowed without
                        # actually committing the shadowed source.
                        v = v.parentVersion()
                        print '  Shadowed from %s=%s' % (n, v)
                        continue
                    print '  Missing trove %s=%s' % (n, v)
                    break
                ti = trv.getTroveInfo()
                clonedVersion = ti.clonedFrom()
                sourceName = ti.sourceName()
                nextVersion = None
                if clonedVersion:
                    nextVersion = clonedVersion
                    print '  Cloned from %s=%s' % (n, nextVersion)
                elif sourceName:
                    n, nextVersion, f = sourceName, v.getSourceVersion(), deps.Flavor()
                    print '  Built from %s=%s' % (sourceName, nextVersion)

                if nextVersion in seen:
                    print '  recursion detected'
                    break
                if nextVersion:
                    seen.add(nextVersion)
                v = nextVersion


class Subtrove(BaseConaryUtil):

    """
    Given a trovespec for a group and a secondary trove name, find all
    occurences of that trove name in the group and print their tuples,
    and whether they are weak and/or missing by default.

    If the subtrove is a package, all components will be displayed also.

    $ ./subtrove.py group-os=conary.rpath.com@rpl:1 conary
    conary=/conary.rpath.com@rpl:devel//1/2.0.18-0.1-1[~!bootstrap is: x86] [weak]
    conary:data=/conary.rpath.com@rpl:devel//1/2.0.18-0.1-1[~!bootstrap is: x86] [weak]
    conary:debuginfo=/conary.rpath.com@rpl:devel//1/2.0.18-0.1-1[~!bootstrap is: x86] [weak] [missing]
    conary:doc=/conary.rpath.com@rpl:devel//1/2.0.18-0.1-1[~!bootstrap is: x86] [weak]
    conary:python=/conary.rpath.com@rpl:devel//1/2.0.18-0.1-1[~!bootstrap is: x86] [weak]
    conary:runtime=/conary.rpath.com@rpl:devel//1/2.0.18-0.1-1[~!bootstrap is: x86] [weak]
    """

    def __init__(self, trovespec, subname):
        super(Subtrove, self).__init__()
        self.main(trovespec, subname)

    def main(self, troveSpec, subName):
        name, version, flavor = parseTroveSpec(troveSpec)
        matches = self._repos.findTrove(None, (name, version, flavor))
        troveTups = sorted(matches, key=lambda x: x[1])
        troves = self._repos.getTroves(troveTups, withFiles=False)
        results = set()
        for trv in troves:
            # Loop through trove refs
            found = False
            out = []
            for (name, version, flavor), byDefault, isStrong in trv.iterTroveListInfo():
                if (':' in subName and subName == name) \
                  or (subName == name.split(':')[0]):
                    out.append((name, version, flavor, byDefault, isStrong))

            if not out:
                print 'No matching subtroves found'

            for name, version, flavor, byDefault, isStrong in sorted(out):
                byDefault = (not byDefault) and ' [missing]' or ''
                isStrong = (not isStrong) and ' [weak]' or ''
                results.add('%s=%s[%s]%s%s' % (name, version, flavor, isStrong, byDefault))

        for result in sorted(results):
            print result





class ListSearchPath(BaseConaryUtil):
    '''
    Given a trovespec for a group, list the search path used for each
    matching built group.
    '''

    def __init__(self, trovespecs):
        super(ListSearchPath, self).__init__()
        self.main(trovespecs)


    def main(self, troveSpecs):
        for troveSpec in troveSpecs:
            # Parse cmdline arguments and fetch that trove
            name, version, flavor = parseTroveSpec(troveSpec)
            matches = sorted(self._repos.findTrove(None, (name, version, flavor)))
            troves = self._repos.getTroves(matches, withFiles=False)

            # Loop through search path used in build
            for trv in troves:
                print '%s=%s[%s]' % trv.getNameVersionFlavor()
                for item in trv.getTroveInfo().searchPath.iter():
                    if isinstance(item, tuple):
                        print '  %s=%s[%s]' % item
                    else:
                        print '  %s' % item.asString()


