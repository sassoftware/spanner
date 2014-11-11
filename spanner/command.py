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

from spanner import worker


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
    paramHelp = '[uri] [plans]...'
    help = "Build git repos from bob-plans"
    requireConfig = True

    def addParameters(self, argDef):
        SpannerCommand.addParameters(self, argDef)
        argDef['branch'] = options.ONE_PARAM
        argDef['cfgfile'] = options.ONE_PARAM
        argDef['dry-run'] = options.NO_PARAM
        argDef['group'] = options.NO_PARAM

    def shouldRun(self):
        if self.uri:
            return True
        logger.error('build command requires a uri')
        return False

    def runCommand(self, cfg, argSet, params, **kw):
        self.cfg = cfg
        self.cfgfile = argSet.pop('cfgfile', None)
        self.branch = argSet.pop('branch', None)
        self.test = argSet.pop('dry-run', False)
        self.group = argSet.pop('group', False)

        if not len(params) >= 3:
            return self.usage()

        self.uri = params[2]
        
        force_builds = params[3:] or []

        if not self.shouldRun():
            logger.info('Builder will not run, exiting.')
            sys.exit(2)


        spanner = worker.Worker(    uri=self.uri, 
                                    force=force_builds, 
                                    branch=self.branch, 
                                    cfgfile=self.cfgfile, 
                                    test=self.test,
                                    )
        spanner.main()

