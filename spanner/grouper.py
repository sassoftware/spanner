import logging
import os
import subprocess
import tempfile
import time
from collections import defaultdict

from conary.lib import log as cny_log

from . import clientfactory
from . import config
from . import git
from . import templates
from . import groups
from . import errors
from .package import Package


logger = logging.getLogger(__name__)


class Grouper(object):

    def __init__(self, uri, branch, cache=None, cfg=None, test=False,
                 plans=None):
        self.uri = uri
        self.cachedir = cache
        self.branch = branch
        self.identifier = '_'.join([self.branch, 
                                    time.strftime('%Y.%m.%d_%H%M.%S')])
        self.prepped = False
        self.fetched = False
        self._cclient = None
        self._cfg = cfg
        if not self._cfg:
            self.getDefaultConfig()
        if not self.cachedir:
            self.cachedir = self._cfg.cacheDir
        self.debug = self._cfg.debugMode
        self.test = test
        self.head = None
        self.plans = plans
        if self.plans:
            self.plans = [os.path.basename(plan) for plan in self.plans]

        if self._cfg.testOnly:
            logger.warn('testOnly set in config file ignoring commandline')
            self.test = self._cfg.testOnly
        self.bobexec = self._cfg.bobExec
        self.logfile = self._cfg.logFile
        self.tmpdir = self._cfg.tmpDir
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        assert os.path.exists(self.tmpdir)
        self.plandir = os.path.join(self.tmpdir, 'plans')
        self.commonDir = self._cfg.commonDir
        self.commonFile = self._cfg.commonFile
        self.packagesDir = self._cfg.packagesDir
        self.force_build = []
        self.commonLabel = None

    def setForceBuild(self, targets):
        '''
        get a list of targets to build regardless
        '''
        for target in targets:
            self.force_build.append(target)

    def getDefaultConfig(self):
        logger.info('Loading default cfg')
        self._cfg = config.SpannerConfiguration()
        self._cfg.read()

    def configureLogging(self, logFile, debug, quiet):
        if debug:
            consoleLevel = logging.DEBUG
            fileLevel = logging.DEBUG
        elif quiet:
            consoleLevel = logging.ERROR
            fileLevel = logging.INFO
        else:
            consoleLevel = logging.ERROR
            fileLevel = logging.INFO
        cny_log.setupLogging(
            logPath=logFile,
            consoleLevel=consoleLevel,
            consoleFormat='apache',
            fileLevel=fileLevel,
            fileFormat='apache',
            logger='builder',
            )

    conaryClientFactory = clientfactory.ConaryClientFactory

    def _getClient(self, force=False):
        if self._cclient is None or force:
            self._cclient = self.conaryClientFactory().getClient(
                model=False)
        return self._cclient

    conaryClient = property(_getClient)

    def _getCfg(self, force=False):
        if self._cfg is None or force:
            self._cfg = self.conaryClientFactory().getCfg()
        return self._cfg

    conaryCfg = property(_getCfg)

    def _temp_file(self, data):
        fd, path = tempfile.mkstemp(prefix='plan.', dir=self.tmpdir)
        try:
            f = os.fdopen(fd, 'w')
            f.write(str(str(data)))
        except Exception, e:
            #FIXME
            raise
        return path

    def _check_remote_repo(self):
        #TODO
        # If repo is not in scm need to solve all the macros to create
        # repo_uri
        remote_repo_prefix = ['http://', 'https://', 'git://', 'ssh://']
        for pre in remote_repo_prefix:
            if self.uri.startswith(pre):
                return True
        assert os.path.exists(self.uri)
        return False

    def _check_remote_heads(self, test, uri, branch=None):
        heads = self.ls_remote(uri, branch)
        for head, commit in heads.items():
            logger.debug('Testing %s %s against %s' % (head, commit, test))
            if commit == test:
                return True
        return False

    def _updateCache(self):
        logger.info('Caching...')
        if not os.path.exists(self.cachedir):
            logger.debug('Making directory for cache at %s' % self.cachedir)
            os.makedirs(self.cachedir)
        logger.info('Updating cachedir at location  %s' % self.cachedir)
        self.updateCache()

    def fetch(self):
        logger.info('Fetching...')
        if not os.path.exists(self.plandir):
            logger.debug('Making directory for plans at %s' % self.plandir)
            os.makedirs(self.plandir)
        logger.info('Checking out sources from %s to %s by way of %s' %
                    (self.repoDir, self.plandir, self.cachedir))
        self.checkout(self.plandir)

    def gather_plans(self):
        logger.debug('Gathering plan files from %s' % self.plandir)
        plans = defaultdict(dict,{ 
                                'packages' : set(),
                                'common'   : set(),
                                'external' : set(),
                            }
                        )

        for root, dirs, files in os.walk(self.plandir):
            # don't add packages if self.plans is set
            if os.path.basename(root) == self._cfg.packagesDir:
                for fn in files:
                    # if user specified plans, only build those plans
                    if self.plans and fn not in self.plans:
                        continue
                    plans.setdefault('packages', set()).add(
                        os.path.join(root, fn))
            if os.path.basename(root) == self._cfg.commonDir:
                for fn in files:
                    plans.setdefault('common', set()).add(
                        os.path.join(root, fn))
            if os.path.basename(root) == self._cfg.externalDir:
                for fn in files:
                    plans.setdefault('external', set()).add(
                        os.path.join(root, fn))
        return plans

    def read_plan(self, path):
        logger.debug('Reading...')
        plan = config.BobConfig()
        plan.read(path)
        logger.info('Reading plan from %s' % path)
        return plan

    def _build(self, path, name=None, version=None, tag=None):
        '''
        @param path: A string representing the path 
                    to the bob plan to be executed
        @type path: String
        @param name: the name of package to be built. 
                required for setting version or tag (optional)
        @type name: String
        @param version: string representation of the commit 
                    from git repo (optional)
        @type version: String
        @param tag: string representation of tag from git repo (optional)
        @type: String
        '''
        cmd = [self.bobexec, path]

        if name and version:
            logger.info('Building package %s=%s' % (name, version))
            '''--set-version=conary="${Version}"'''
            logger.debug('Because of an ugly hack by W '
                         'we have to pass the macro for the name '
                         'bob-5 should fix this')
            #versionline = '--set-version=%s=%s' % (name, version)
            pkgmacro = '%(packageName)s'
            versionline = '--set-version=%s=%s' % (pkgmacro, version)
            cmd.append(versionline)
        if name and tag:
            logger.info('Building package %s with tag=%s' % (name, tag))
            '''--set-tag=conary="${Tag}"'''
            tagline = '--set-tag=%s=%s' % (name, tag)
            cmd.append(tagline)

        logger.debug('Calling bob\n%s' % ' '.join(cmd))
        if self.test:
            return 0, ' '.join(cmd)

        p = subprocess.Popen(cmd)
        p.communicate()
        return p.returncode, ' '.join(cmd)

    def handler(self, pkgs):
        tobuild = set([])
        for name, pkg in pkgs.iteritems():
            for _p in pkg:
                if _p.change:
                    logger.info('%s has changed adding to build set' % _p.name)
                    tobuild.add(_p)
        return tobuild

    def prep(self):
        if not self.prepped:
            self._updateCache()
            self.prepped = True

        if self.prepped:
            # FIX ME  
            # Does this belong here? Should move to own function
            heads = self.ls_remote(self.uri, self.branch)
            self.head = [x for x in heads][0]
            assert self.head
            check = self._check_remote_heads(heads[self.head], self.uri)
            # TODO
            # One would think you would want to check self.fetched 
            # But probably safe to run fetch code again anyway
            if check:
                self.fetch()
                self.fetched = True
                return True
        # END
        return False



    def gather_packages(self, plans):


        logger.info('Gathering info from git repos located at '
                    'URI : %s Branch : %s ' % (self.uri, self.branch))

        data = defaultdict()

        for fn in plans:
            if os.path.exists(fn):
                plan = self.read_plan(fn)
                macros = plan.getMacros()

                # Check plans for branch
                branch = macros.get('sourceControlBranch', None)
                if branch is None:
                    raise errors.SpannerBranchMissingError([branch, self.branch])
                if branch != self.branch:
                    raise errors.SpannerBranchError([branch, self.branch])
                # END

                for target in plan.getTarget():
                    logger.info('Working on %s' % target)
                    repositories = None
                    try:
                        repositories = plan.getRepositories()
                    except:
                        logger.warn('Unable to read repositories from bob plan')
                        macros.update({'branch': self.branch})
                        repositories = plan.getRepositories(macros)
                    label = plan.getTargetLabel()
                    logger.debug('Target Label : %s' % label.asString())
                    # Create initial package
                    pkg = Package(  
                                    name=target,
                                    target=target,
                                    change=False,
                                    branch=self.branch,
                                    repositories=repositories,
                                    label=label,
                                    scm=plan.scm,
                                    bobplan=fn,
                                )

                    # Try and find conary versions 
                    updates = defaultdict()
                    revision = None
                    version = None
                    query = { target: { label: None, },}
                    latest = self.conaryClient.repos.getTroveLeavesByLabel(query)
                    if latest:
                        logger.debug('Latest Version : %s' % str(latest))
                        logger.debug('%s found on %s' % (target, pkg.label))
                        versions = latest[target]
                        version = max(versions)
                        revision = version.trailingRevision().version  
                        logger.debug('Found revision %s of %s' % (str(revision),target))

                    
                    updates.update({'revision': revision,
                                    'version': version,
                                    'latest': latest,
                                    })

                    # Make sure we know the uri 

                    if repositories:
                        # NEED TO MAKE git-repo a cfg item
                        scm_type, scm_uri, _ = repositories[self._cfg.gitTarget]
                    else:
                        scm_uri = plan.scm[self._cfg.gitTarget].split(None, 1)[-1]

                    if scm_uri:

                        scm_uri %= macros

                        logger.debug('SCM uri : %s' % scm_uri)

                        if '?' in scm_uri:
                            logger.debug('Remove the branch from the uri')
                            scm_uri, branch = scm_uri.split('?', 1)
                            if branch != self.branch:
                                logger.warn('%s branch in config does not match '
                                            '%s branch for project' %
                                            (branch, self.branch))
                                assert branch == self.branch
                            # TODO ERROR if the branch
                            # raise errors.SpannerBranchError([branch, self.branch])

                        if scm_uri:
                            info = self.ls_remote(scm_uri, self.branch)
                            commit = info.get(self.head, None)

                            logger.debug('git commit : %s' % str(commit))

                            updates.update({'commit': commit, 'uri': scm_uri})

                            # Start by assuming package did not change
                            change = False

                            if info:
                                # We need proof the pkg is in branch
                                # output in info is a good start
                                if commit:
                                    # This means we found the branch in info
                                    # and extracted the commit record
                                    # Now we check it against package on label
                                    # if no match the package changed
                                    if revision and not commit.startswith(
                                            revision.split('.')[-1]):
                                        logger.debug('Git Commit %s does not start '
                                                    'with Package revision %s' % (commit, revision))
                                        logger.debug('Package %s marked changed' % target)
                                        change = True

                                if not revision:
                                    # If we have info but did not find the revision
                                    # then we assume the package is new to the branch
                                    # and needs to be built
                                    change = True

                            if target in self.force_build:
                                # if --force-build specified at command line
                                # we need to build that target
                                change = True

                            if not change:
                                logger.debug('Package %s revision %s '
                                        'matches Git repo commit %s' % (target, revision, commit))
                            updates.update({'change': change})
                        else:
                            # At this point there is no reason to try any more
                            logger.debug('Not Good. Did not find scm_uri')
                            assert scm_uri

                    pkg.update(updates)

                    if target and repositories:
                        data.setdefault(target, set()).add(pkg)
        return data

    def build(self):
        # TODO Change prep to cache... unwind names
        self.prep()
        if self.fetched:
            self.plans = self.gather_plans()
            packages = self.gather_packages(self.plans['packages'])
            tobuild = self.handler(packages)
            built_packages = []
            failed_packages = []
            seen_plans = []
            skipped = []
            for pkg in tobuild:
                # lets not build pkgs more than once
                if pkg.bobplan not in seen_plans:
                    seen_plans.append(pkg.bobplan)
                else:
                    skipped.append(pkg.name)
                    pkg.log = 'Built in %s' % pkg.bobplan
                    packages.setdefault(pkg.name, set()).add(pkg)
                    continue

                rc, cmd = self._build(pkg.bobplan)
                pkg.log = ('Failed: %s' if rc else 'Success: %s') % cmd
                packages.setdefault(pkg.name, set()).add(pkg)
                if rc:
                    failed_packages.append(pkg)
                else:
                    built_packages.append(pkg)

            if self.test:
                for name, pkgs in packages.items():
                    for pkg in pkgs:
                        logger.info('%s  :  %s\n' % (pkg.name, pkg.log))
                logger.info('List of plans built: %s' % seen_plans)
                logger.info('List of skipped packages: %s' % skipped)

            logger.info('List of packages built: %s' %
                        [pkg.name for pkg in built_packages])

            if failed_packages:
                logger.warn('List of failed package builds: %s' %
                            [pkg.name for pkg in failed_packages])

        return packages, built_packages, failed_packages

    def buildGroup(self, packages, groupname=None, external=None):
        # pkgs have to be formated into txt for the recipe template
        # either it is a comma seperated string of names 
        # or a string of names=version
        # TODO add code to handle no version
        
        if not self.plans:
            self.prep()
            if self.fetched:
                self.plans = self.gather_plans()
       
        fn = [ x for x in self.plans['common'] 
                            if x.endswith(self._cfg.groupConfig) ][0]

        group_plan = self.read_plan(fn)

        macros = group_plan.getMacros()

        if macros.get('includeExternal') or external:
            external_plans = self.plans['external']
            if external_plans:
                external_packages = self.gather_packages(external_plans)
        
        groupName = macros.get('groupName', 'group-foobar')

        if groupname and groupname.startswith('group-'):
            groupName = groupname

        groupLabel = group_plan.getTargetLabel()

        pkgsList = []

        for name, pkgs in packages.items():
            for pkg in pkgs:
                if pkg.version:
                    pkgsList.append('%s=%s' % (pkg.name, str(pkg.version)))
                else:
                    pkgsList.append('%s' % (pkg.name))

        if external_packages:
            for name, pkgs in external_packages.items():
                for pkg in pkgs:
                    pkgsList.append('%s=%s' % (pkg.name, str(pkg.version)))

        logger.debug('Building group for %s' % groupName)
        if self.test:
            logger.info('List of packages in group : %s' % str(pkgsList))
            return

        template = templates.GroupTemplate( name=groupName,
                                            version=self.identifier,
                                            pkgs=pkgsList,
                                            label=groupLabel,
                                        )

        grp = groups.GroupBuilder(template)

        return grp.fricassee()      

    def main(self):
        # TODO Finish buildGroup
        return self.build()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

