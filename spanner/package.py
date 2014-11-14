import logging

from conary import trovetup
from conary import versions

logger = logging.getLogger(__name__)


class Package(object):
    __slots__ = ['name', 'target', 'label', 'repositories', 'controllers',
                 'buildLabel', 'targetLabel', 'sourceLabel',
                 'commit', 'branch', 'tag', 'allversions', 'latest',
                 'version', 'flavor', 'revision', 'uri', 'change',
                 'log', 'bobplan', 'next', 'scm',
                ]

    def __init__(self, **kwargs):
        for s in self.__slots__:
            setattr(self, s, kwargs.pop(s, None))

    def __repr__(self):
        return self.name

    def update(self, kwds):
        for key, value in kwds.items():
            setattr(self, key, value)

    def get(self, flag):
        return getattr(self, flag)

    def getTroveTuples(self):
        trovetupes = []
        if self.latest:
            for version, flavors in self.latest.iteritems():
                for flavor in flavors:
                    trovetupes.append(trovetup.TroveTuple((self.name, version, flavor)))
        else:
            if self.version:
                trovetupes.append(trovetup.TroveTuple((self.name, self.version, self.flavor)))
            else:
                if self.label:
                    ver = '/'.join(['',self.label.asString()])
                    version = versions.VersionFromString(ver)
                    trovetupes.append(trovetup.TroveTuple((self.name, version, self.flavor)))
        return trovetupes

    def getTroveSpecs(self):
        trovespecs = []
        if self.latest:
            for version, flavors in self.latest.iteritems():
                for flavor in flavors:
                    trovespecs.append(trovetup.TroveSpec('%s=%s%s' % (self.name, version, flavor)))
        else:
            trovespecs.append(trovetup.TroveSpec('%s=%s%s' % (
                self.name, self.version, self.flavor or '' )))
        return trovespecs

    @property
    def items(self):
        return self.__slots__

if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()
