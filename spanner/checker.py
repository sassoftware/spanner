import logging
import os

from . import config
from . import errors
from . import package
from . import controller
from . import factory
from rev_file import RevisionFile


logger = logging.getLogger(__name__)

class PlanUtils(object):

    def _read_plan(self, path):
        '''
        read individual plan
        @param path: path to plan
        @type path: string
        @return cfg object
        '''
        logger.debug('Reading...')
        plan = config.BobConfig()
        plan.read(path)
        logger.info('Reading plan from %s' % path)
        return plan

    def _get_repositories(self, plan, branch=None):
        repositories = {}
        macros = plan.getMacros()
        try:
            repositories = plan.getRepositories()
        except:
            logger.warn('Unable to read repositories from bob plan')
            macros.update({'branch': branch})
            repositories = plan.getRepositories(macros)
        return repositories

    def _get_controllers(self, plan, branch=None):
        controllers = {}
        base = None
        repositories = self._get_repositories(plan, branch)
        for name, values in repositories.iteritems():
            ctrltype = values[0].upper()
            paths = [ x for x in values[1].split('/') if x ]
            rev = None
            if len(values) == 3:
                branch = values[2]
            if ctrltype == 'WMS':
                base = plan.wmsBase
                path = '/'.join(paths)
                tip = self.rf.revs.get(path)
                if tip:
                    rev = tip.get('id')
            if ctrltype in [ 'GIT', 'HG' ]:
                base = '//'.join(paths[:2])
                if base.startswith('file'):
                    base = '///'.join(paths[:2])
                path = '/'.join(paths[2:])
                if len(path.split('?')) == 2:
                    path, branch = path.split('?')
            if base and path:
                ctrlr = controller.Controller.create(   
                                                    ctrltype, 
                                                    base, 
                                                    path, 
                                                    branch,
                                                    rev,
                                                    )
                controllers.setdefault(name, ctrlr)
        return controllers


class Checker(PlanUtils):

    def __init__(self, plans, cfg, force=[], branch=None, test=False):
        self.plans = plans
        self.test = test
        self.cfg = cfg
        self.force_build = force
        self.branch = branch
        self.rf = RevisionFile()

    def setForceBuild(self, targets):
        '''
        get a list of targets to build regardless
        '''
        for target in targets:
            self.force_build.append(target)

    def _initial_packages(self, path):

        '''
        plans can contain more than one target
        targets are translated into pkgs.
        @param path: path to plan
        @type path: String
        @return pkgs: a set of pkg objects
        '''
        pkgs = set()
        assert os.path.exists(path)
        plan = self._read_plan(path)
        macros = plan.getMacros()

        # Check plans for branch in plan
        branch = macros.get('branch', None)

        if not branch:
            # Support for legecy plans
            branch = macros.get('sourceControlBranch', None)

        branch %= macros

        # Make sure if we specified a branch it matches the plan
        if self.branch:
            if branch is None:
                raise errors.SpannerBranchMissingError([branch, self.branch])
            if branch != self.branch:
                raise errors.SpannerBranchError([branch, self.branch])
        # END           

        for target in plan.getTargets():
            logger.info('Working on %s' % target)

            label = plan.getTargetLabel()
            logger.debug('Target Label : %s' % label.asString())
            repositories = self._get_repositories(plan, branch)
            controllers = self._get_controllers(plan, branch)   
            # Create initial package
            pkg = package.Package(  name=target,
                            target=target,
                            change=False,
                            branch=branch,
                            repositories=repositories,
                            label=label,
                            controllers=controllers,
                            bobplan=path,
                        )
            pkgs.add(pkg)
        return pkgs

    def _get_commit_hash(self, pkg):
        ''' 
            pkg = pkg object with ctrlrs
            The commit hash we want to build 
            needs to be from the revisions.txt if supplied
        '''
        commit = None
        ctrlr = pkg.controllers.get(pkg.name)
        if ctrlr:
            commit = ctrlr.revision
        return { 'commit' : commit }

    def _get_conary_version(self, pkg):
        # Try and find conary versions 
        cc = factory.ConaryClientFactory().getClient()
        revision = None
        version = None
        query = { pkg.target: { pkg.label: None, },}
        latest = cc.repos.getTroveLeavesByLabel(query)
        if latest:
            logger.debug('Latest Version : %s' % str(latest))
            logger.debug('%s found on %s' % (pkg.target, pkg.label))
            versions = latest[pkg.target]
            version = max(versions)
            revision = version.trailingRevision().version  
            logger.debug('Found revision %s of %s' % (str(revision),pkg.target))
            
        return {'revision': revision, 'version': version, 'latest': latest}

    def _detect_change(self, pkg):
        # Start by assuming package did not change
        change = False
        if pkg.commit:
            # This means we found the branch in info
            # and extracted the commit record
            # Now we check it against package on label
            # if no match the package changed
            if pkg.revision and not pkg.commit.startswith(
                    pkg.revision.split('.')[-1]):
                logger.debug('Git Commit %s does not start '
                            'with Package revision %s' % (pkg.commit, pkg.revision))
                logger.debug('Package %s marked changed' % pkg.target)
                change = True

        if not pkg.revision:
            # If we have info but did not find the revision
            # then we assume the package is new to the branch
            # and needs to be built
            change = True

        if pkg.target in self.force_build:
            # if --force-build specified at command line
            # we need to build that target
            change = True

        if not change:
            logger.debug('Package %s revision %s '
                    'matches Git repo commit %s' 
                    % (pkg.target, pkg.revision, pkg.commit))

        return {'change': change}


    def _check_plans_in_dir(self, path):
        packages = {}
        for pkg in self._initial_packages(path):
            # Commit hash we want to build
            pkg.update(self._get_commit_hash(pkg))
            pkg.update(self._get_conary_version(pkg))
            pkg.update(self._detect_change(pkg))
            if pkg.target and pkg.repositories:
                packages.setdefault(pkg.target, set()).add(pkg)
        return packages

    def _get_packages(self, plans):
        data = {}
        for section, paths in plans.iteritems():
            if section in [ self.cfg.projectsDir, 
                            self.cfg.externalDir,
                            self.cfg.productsDir,
                            ]:
                pkgs = {}
                for path in paths:
                    pkgs.update(self._check_plans_in_dir(path))
                data.setdefault(section, pkgs)

            # TODO Eval each dir seperately if necessary
            #if section == self.cfg.externalDir:
                # TODO Eval the external packages
                #data.setdefault(section, paths)

            #if section == self.cfg.productsDir:
                # TODO Eval the products packages
                #data.setdefault(section, paths)

        return data   

    def check(self):
        return self._get_packages(self.plans)

    def main(self):
        return self.check()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

