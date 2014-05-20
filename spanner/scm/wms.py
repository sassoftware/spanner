import urllib
import urllib2
import requests

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
        self.repos = None
        self.poll = None 
        silo, subpath = self.path.split('/', 1)
        self.pathq = self._quote(silo) + '/' + self._quote(subpath)
        self.repos = self.base + '/api/repos/' + self.pathq
        self.locator = self.repos + '/' + 'show_url'
        if self.branch:
            self.poll = self.repos + '/poll/' + self._quote(self.branch)

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

    def _getTip(self):
        result = self.fetchlines(self.poll)
        assert len(result) == 1
        path, branch, tip = result[0].split()
        assert len(tip) == 40
        return branch, tip

    def getTip(self):
        return self._getTip()[1]

    def getGitUri(self):
        #FIXME might need to append .git
        return self.fetchlines(self.locator)

    def readRevisions(self, filename):
        blob = ''
        with open(filename, 'a') as revisions:
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

    @staticmethod
    def _quote(foo):
        return urllib.quote(foo).replace('/', ':')
        
