import urllib
import urllib2
import requests
import subprocess
import os

from conary.lib.util import copyfileobj

from forester import scm

import logging

logger = logging.getLogger(__name__)


class WmsRepository(scm.ScmRepository):

    TAGS = ('name', 'silo', 'branch', 
            'head', 'path', 'pathq', 
            'repos', 'poll', 'locator',
            'uri',
            )

    def __init__(self, base, path, branch=None):
        self.base = base
        self.path = path
        # FIXME Hardcoded default ot master for now
        self.branch = branch or 'master'
        self.pathq = None
        #self.repos = None
        self.revision = None
        self.tag = None
        self.poll = None 
        silo, subpath = self.path.split('/', 1)
        self.tar = subpath.replace('/','_') + '.tar'
        self.pathq = self._quote(silo) + '/' + self._quote(subpath)
        #self.repos = self.base + '/api/repos/' + self.pathq
        self.locator = self.repos + '/' + 'show_url'
        self.archive = self.repos + '/archive'
        if self.branch:
            self.poll = self.repos + '/poll/' + self._quote(self.branch)
        if not self.revision:
            self.setRevision()

    def settag(self, tag):
        self.tag = tag

    @property
    def repos(self):
        silo, subpath = self.path.split('/', 1)
        pathq = self._quote(silo) + '/' + self._quote(subpath)
        return self.base + '/api/repos/' + pathq

    @staticmethod
    def _quote(foo):
        return urllib.quote(foo).replace('/', ':')


    def fetchlines(self, uri):
        req = requests.get(uri)
        if req.ok:
            return [ x for x in req.text.split('\n') if x ]
        return [ 'ERROR', req.status_code ]

    def fetch(self, uri):
        req = requests.get(uri)
        if req.ok:
            return req.text
        return req.status_code

    def _findTip(self, revisions):
        for result in revisions:
            path, branch, tip = result.split()
            if path == self.pathq:
                break
        assert len(tip) == 40
        return branch, tip

    def getTip(self):
        revisions = self.fetchlines(self.poll)
        return self._findTip(revisions)[1]

    def setFromTip(self):
        revisions = self.fetchlines(self.poll)
        branch, tip = self._findTip(revisions)
        # FIXME Not sure we should set branch here
        # might be safer to check the branch
        # assert self.branch == branch
        if not self.branch:
            self.branch = branch
        self.revision = tip
        self.revIsExact = True

    def setFromFile(self, filename):
        results = self.readRevisions(filename)
        revisions = [ x for x in results.split('\n') if x ]
        branch, tip = self.findTip(revisions)
        # FIXME Not sure we should set branch here
        # might be safer to check the branch
        # assert self.branch == branch
        if not self.branch:
            self.branch = branch
        self.revision = tip
        self.revIsExact = True

    def getGitUri(self):
        #FIXME might need to append .git
        result = self.fetchlines(self.locator)
        assert len(result) == 1
        return result[0]

    def readRevisions(self, filename):
        blob = ''
        with open(filename, 'r') as revisions:
            blob = revisions.read()
        return blob

    def writeRevisions(self, filename, blob):
        with open(filename, 'a') as revisions:
            revisions.write(blob)

    def fetchRevisions(self, uri=None):
        if not uri and self.poll:
            uri = self.poll
        return self.fetch(uri)

    def parseRevisionsLine(self, fl):
        path, branch, head = fl.split()
        silo, subpath = path.split('/', 1)
        name = subpath.split('/')[-1]
        pathq = self._quote(silo) + '/' + self._quote(subpath)
        repos = self.base + '/api/repos/' + pathq
        poll = repos + '/poll/' + self._quote(branch)
        locator = repos + '/' + 'show_url'
        uri = self.fetchlines(locator)[0]
        return name, silo, branch, head, path, pathq, repos, poll, locator, uri
        
    def parseRevisions(self, blob):
        data = {}
        filelines = [ x for x in blob.split('\n') if x]
        for fl in filelines:
            info = self.parseRevisionsLine(fl)    
            data.setdefault(info[0], {}).update(dict(zip(self.TAGS,info)))
        return data
 
    def parseRevisionsFromUri(self, uri=None):
        if not uri and self.poll:
            uri = self.poll
        revisions = self.fetchRevisions(uri)
        return self.parseRevisions(revisions)

    def parseRevisionsFromFile(self, filename):
        revisions = self.readRevisions(filename)
        return self.parseRevisions(revisions)

    def updateCache(self):
        pass

    def _archive(self, compress=''):
        return urllib.quote(os.path.basename(self.path)
                + '-' + self.getShortRev()
                + '.tar' + compress)

    def snapshot(self, workDir, subtree=None):
        '''
        http://wheresmystuff.unx.sas.com/api/repos/scc/build-tools/archive/78eed1cae30790e65ee599b04f93f23e93b84641/build-tools.tar
        Need to parseRevisionLine and extract the head
        then download the head and explode it into the workDir
        '''
        archive = self._archive()
        data = urllib.urlencode([('subtree', subtree)]) if subtree else None
        f = urllib2.urlopen(self.repos + '/archive/'
                    + self.revision + '/' + archive, data=data)
        tar = subprocess.Popen(['tar', '-x'], stdin=subprocess.PIPE,
                cwd=workDir)
        while True:
            d = f.read(10000)
            if not d:
                break
            tar.stdin.write(d)
        tar.stdin.close()
        tar.wait()
        if tar.returncode:
            raise RuntimeError("tar exited with status %s" % tar.returncode)
        prefix = archive.rsplit('.', 1)[0]
        return prefix

    def getAction(self, extra=''):
        f = urllib2.urlopen(self.repos + '/show_url')
        url = f.readline().strip()
        f.close()
        return 'addGitSnapshot(%r, branch=%r, tag=%r%s)' % (
                url, self.branch, self.getShortRev(), extra)
 
    def fetchArchive(self, conarySource, snapPath):
        if os.path.exists(snapPath):
            return
        archive = urllib.quote(os.path.basename(snapPath))
        url = (self.repos + '/archive/'
                + urllib.quote(self.revision) + '/' + archive)
        f_in = urllib2.urlopen(url)
        with open(snapPath, 'w') as f_out:
            copyfileobj(f_in, f_out)
        f_in.close()

    def setRevision(self, rev=None, filename=None):
        if filename:
            self.setFromFile(filename)
        if rev:
            self.revision = rev['id']
            self.revIsExact = True
            assert self.branch == rev['branch']
        else:
            self.setFromTip()

