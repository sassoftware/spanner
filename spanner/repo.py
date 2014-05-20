


class Repo(object):
    __slots__ = [   'name', 
                    'branch', 
                    'uri', 
                    'scm', 
                    'base', 
                    'path',
                    'silo',
                    'pathq',
                    'repos', 
                    'poll', 
                    'control', 
                    'wms', 
                    'locator',
                    'commit', 
                    'tags', 
                    'head', 
                    'revision', 
                    'change', 
                    'archive', 
                    'bobplan'
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

    @property
    def items(self):
        return self.__slots__


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

