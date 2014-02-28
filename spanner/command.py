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


import logging
import sys

from conary.lib import command, options

from spanner import builder


logger = logging.getLogger(__name__)


class SpannerCommand(command.AbstractCommand):

    def addParameters(self, argDef):
        command.AbstractCommand.addParameters(self, argDef)
        argDef['quiet'] = options.NO_PARAM
        argDef['debug-logging'] = options.NO_PARAM

    def runCommand(self, *args, **kw):
        pass


class HelpCommand(SpannerCommand):
    """
    Displays help about this program or commands within the program.
    """
    commands = ['help']
    help = 'Display help information'

    def runCommand(self, cfg, argSet, args, **kwargs):
        command, subCommands = self.requireParameters(args, allowExtra=True)
        if subCommands:
            command = subCommands[0]
            commands = self.mainHandler._supportedCommands
            if not command in commands:
                print >> sys.stderr, "%s: no such command: '%s'" % (
                    self.mainHandler.name, command)
                sys.exit(1)
            print >> sys.stderr, commands[command].usage()
        else:
            print >> sys.stderr, self.mainHandler.usage()


class ConfigCommand(SpannerCommand):
    commands = ['config']
    help = 'Display the current configuration'

    def runCommand(self, cfg, argSet, args, **kwargs):
        cfg.setDisplayOptions(hidePasswords=True,
                              showContexts=False,
                              prettyPrint=True,
                              showLineOrigins=False)
        if argSet:
            return self.usage()
        if (len(args) > 2):
            return self.usage()
        else:
            cfg.display()


class BuilderCommand(SpannerCommand):
    commands = ['build']
    paramHelp = '[plans]...'
    help = "Build git repos from bob-plans"
    requireConfig = True

    def addParameters(self, argDef):
        SpannerCommand.addParameters(self, argDef)
        argDef['branch'] = options.MULT_PARAM
        argDef['cachedir'] = options.ONE_PARAM
        argDef['repo'] = options.ONE_PARAM
        argDef['dry-run'] = options.NO_PARAM
        argDef['group'] = options.ONE_PARAM
        argDef['group-label'] = options.ONE_PARAM
        argDef['external'] = options.NO_PARAM
        argDef['force-build'] = options.MULT_PARAM
        argDef['xml'] = options.NO_PARAM
        argDef['json'] = options.NO_PARAM

    def shouldRun(self):
        if self.branches and self.repo:
            return True
        logger.error('build command requires --repo '
                     'and at least one --branch <branch>')
        return False

    def runCommand(self, cfg, argSet, params, **kw):
        self.cfg = cfg
        self.branches = argSet.pop('branch', [])
        self.cachedir = argSet.pop('cachedir', 'spanner-cache')
        self.repo = argSet.pop('repo', None)
        self.test = argSet.pop('dry-run', False)
        self.group = argSet.pop('group', False)
        self.group_label = argSet.pop('group-label', False)
        self.external = argSet.pop('external', False)
        self.targets = argSet.pop('force-build', [])
        self.xml = argSet.pop('xml', False)
        self.json = argSet.pop('json', False)

        plans = params[2:]

        if not self.shouldRun():
            logger.info('Builder will not run, exiting.')
            sys.exit(2)

        for branch in self.branches:
            spanner = builder.Builder(self.repo, branch,
                                      self.cachedir, self.cfg,
                                      self.test, plans)
            if self.targets:
                spanner.setForceBuild(self.targets)
            packages, built_packages, failed_packages = spanner.build()
            if built_packages and self.group:
                spanner.buildGroup(packages, self.group, self.external)
            # we only consider it an error if no packages were built
            # and any failed to build
            return (1 if not packages and failed_packages else 0)
