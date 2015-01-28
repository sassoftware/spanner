#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
'''
Actions to read plans, create package objects, set flags for changes 
between conary version and SCM repository
'''

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
    '''
    B{PlanUtils}
    tools for reading and processing plans
    '''

    def __init__(self):
        self.revision_file = RevisionFile()

    @classmethod
    def read_plan(cls, path):
        '''
        read individual plan
        @param path: path to plan
        @type path: C{string}
        @return: cfg object
        '''
        logger.debug('Reading...')
        plan = config.BobConfig()
        plan.read(path)
        logger.info('Reading plan from %s' % path)
        return plan

    @classmethod
    def get_repositories(cls, plan, branch=None):
        '''read repositories from bob-plans'''
        repositories = {}
        macros = plan.getMacros()
        try:
            repositories = plan.getRepositories()
        except Exception, err:
            logger.warn('Unable to read repositories from bob plan : %s' % err)
            macros.update({'branch': branch})
            repositories = plan.getRepositories(macros)
        return repositories

    def get_controllers(self, plan, branch=None):
        '''
        Figure out from the plan what type of controller
        to use for fetching from repo
            - WMS
            - GIT
            - HG    -- Not Implemented
            - LOCAL -- Not Implemented

        @param plan: uri to plan
        @type uri: C{string}
        '''
        controllers = {}
        base = None
        repositories = self.get_repositories(plan, branch)
        for name, values in repositories.iteritems():
            ctrltype = values[0].upper()
            paths = [ x for x in values[1].split('/') if x ]
            rev = None
            if len(values) == 3:
                branch = values[2]
            if ctrltype == 'WMS':
                base = plan.wmsBase
                path = '/'.join(paths)
                tip = self.revision_file.revs.get(path)
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
    '''
    B{Checker}
    Check plans and create package objects
    @param plans: set of plan objects
    @param cfg: cfg object
    @keyword force: list of targets to build regardless of change state
    @keyword branch: branch of repo to work on
    @keyword test: Boolean to trigger a dry run 
    '''

    def __init__(self, plans, cfg, force=None, branch=None, test=False):
        super(Checker, self).__init__()
        self.plans = plans
        self.cfg = cfg
        self.force_build = force or []
        self.branch = branch
        self.test = test

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
        @type path: C{string}
        @return pkgs: a set of pkg objects
        '''
        pkgs = set()
        assert os.path.exists(path)
        plan = self.read_plan(path)
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
            repositories = self.get_repositories(plan, branch)
            controllers = self.get_controllers(plan, branch)   
            # Create initial package
            bobsect = plan.getSection('target:%s'%target)
            scm = bobsect.scm or bobsect.sourceTree.split()[0]
            pkg = package.Package(  name=target,
                            target=target,
                            change=False,
                            branch=branch,
                            repositories=repositories,
                            label=label,
                            controllers=controllers,
                            bobplan=path,
                            scm=scm,
                        )
            pkgs.add(pkg)
        return pkgs

    @classmethod
    def _get_commit_hash(cls, pkg):
        ''' 
        The commit hash we want to build 
        needs to be from the revisions.txt if supplied
        @param pkg: pkg object with ctrlrs
        '''
        commit = None
        ctrlr = pkg.controllers.get(pkg.scm)
        if not ctrlr and pkg.controllers:
            # TODO
            # add revision.txt info to source pkg metadata 
            # so we can figure out the revisions 
            # without knowing the conary version
            # FIXME
            # Currently do not support multiple 
            # scms not named after package
            assert len(pkg.controllers) == 1
            ctrlr = pkg.controllers.itervalues().next()
        if ctrlr:
            commit = ctrlr.revision
        return { 'commit' : commit }

    def _get_commit_hashes(self, packages):
        '''iter over packages and set  commit hash values'''
        for name, pkgs in packages.items():
            for pkg in pkgs:
                pkg.update(self._get_commit_hash(pkg))
                packages.setdefault(name, set()).add(pkg)
        return packages

    @classmethod
    def _get_conary_version(cls, pkg):
        '''Tries to find conary version of a package'''
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
            logger.debug('Found revision %s of %s' % (str(revision), 
                                                            pkg.target))
            
        return {'revision': revision, 'version': version, 'latest': latest}

    @classmethod 
    def _get_conary_versions(cls, packages):
        '''
        iter through a set of packages and find conary version of ea.
        @return: updated package set
        '''
        cc = factory.ConaryClientFactory().getClient()
        query = {}

        # Only make one query to the repo
        for _, pkgs in packages.items():
            for pkg in pkgs:
                query.update({ pkg.target: { pkg.label: None, },})
        
        latestTroves = cc.repos.getTroveLeavesByLabel(query)
        
        for name, pkgs in packages.items():
            for pkg in pkgs:
                latest = latestTroves.get(pkg.target)
                if latest:
                    logger.debug('%s found on %s' % (pkg.target, pkg.label))
                    version = max(latest)
                    logger.debug('Latest Version : %s' % version.asString())
                    revision = version.trailingRevision().version  
                    logger.debug('Found revision %s of %s' % (str(revision),
                                                    pkg.target))
            
                    pkg.update({'revision': revision, 
                            'version': version, 
                            'latest': latest})
                packages.setdefault(name, set()).add(pkg)
        return packages

    def _detect_change(self, pkg):
        '''
        detect if a package has changed
        @return: dict { 'change' : Boolean }
        '''
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

    def _detect_changes(self, packages):
        '''loop through packages looking for changes'''
        for name, pkgs in packages.items():
            for pkg in pkgs:
                pkg.update(self._detect_change(pkg))
                packages.setdefault(name, set()).add(pkg)
        return packages
        
    def _check_plans_in_dir(self, path):
        '''create initial plan package object for each plan in a directory'''
        packages = {}
        for pkg in self._initial_packages(path):
            if pkg.target and pkg.repositories:
                #packages.setdefault(pkg.target, set()).add(pkg)
                packages.setdefault(path, set()).add(pkg)
        return packages


    def _get_packages(self, plans):
        '''create a dict of all the sections and plans'''
        data = {}
        for section, paths in plans.iteritems():
            if section in [ self.cfg.projectsDir, 
                            self.cfg.externalDir,
                            self.cfg.productsDir,
                            ]:
                pkgs = {}
                for path in paths:
                    pkgs.update(self._check_plans_in_dir(path))
                pkgs = self._get_conary_versions(pkgs)
                pkgs = self._get_commit_hashes(pkgs)
                pkgs = self._detect_changes(pkgs)
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
        '''
        Check all sections for plans and 
        @return: C{dict} of { section : packages }
        '''
        return self._get_packages(self.plans)

    def main(self):
        '''Main call for Checker'''
        return self.check()


if __name__ == '__main__':
    import sys
    from conary.lib import util
    sys.excepthook = util.genExcepthook()

