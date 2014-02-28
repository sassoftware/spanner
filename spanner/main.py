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


import errno
import logging
import sys

from conary.lib import log as cny_log
from conary.lib import mainhandler

from spanner import command
from spanner import config
from spanner import constants
from spanner import errors

logger = logging.getLogger(__name__)


class SpannerMain(mainhandler.MainHandler):

    name = 'spanner'
    version = constants.version

    abstractCommand = command.SpannerCommand
    configClass = config.SpannerConfiguration
    commandList = [
        command.HelpCommand,
        command.ConfigCommand,
        command.BuilderCommand,
        ]

    setSysExcepthook = False

    def configureLogging(self, logFile, debug, quiet):
        if debug:
            consoleLevel = logging.DEBUG
            fileLevel = logging.DEBUG
        elif quiet:
            consoleLevel = logging.ERROR
            fileLevel = logging.INFO
        else:
            consoleLevel = logging.INFO
            fileLevel = logging.INFO
        cny_log.setupLogging(
            logPath=logFile,
            consoleLevel=consoleLevel,
            consoleFormat='apache',
            fileLevel=fileLevel,
            fileFormat='apache',
            logger='spanner',
            )

    def runCommand(self, command, cfg, argSet, *args, **kw):
        debug = argSet.get('debug-logging', False)
        if cfg.debugMode:
            debug = cfg.debugMode
        if debug:
            logger.debug('Running in debug mode...')
        quiet = argSet.get('quiet', False)
        self.configureLogging(cfg.logFile, debug, quiet)
        logger.info("Running command: %s" % command.commands[0])
        response = mainhandler.MainHandler.runCommand(self, command, cfg,
                                                      argSet, *args, **kw)
        logger.info("Command finished: %s" % command.commands[0])
        return response


def _main(argv, MainClass):
    """
    Wrapper method that handles all remaining uncaught exceptions from
    spanner.

    @param argv: standard argument vector
    @param MainClass: class object that implements a main() method.
    """
    if argv is None:
        argv = sys.argv
    #pylint: disable-msg=E0701
    # pylint complains about except clauses here because we sometimes
    # redefine debuggerException
    debuggerException = Exception
    try:
        argv = list(argv)
        debugAll = '--debug-all' in argv
        if debugAll:
            argv.remove('--debug-all')
        else:
            debuggerException = errors.SpannerError
        sys.excepthook = errors.genExcepthook(debug=debugAll,
                                              debugCtrlC=debugAll)
        rc = MainClass().main(argv, debuggerException=debuggerException)
        if rc is None:
            return 0
        return rc
    except errors.SpannerError, e:
        print e
        return 1
    except debuggerException, err:
        raise
    except IOError, e:
        # allow broken pipe to exit
        if e.errno != errno.EPIPE:
            raise
    except KeyboardInterrupt:
        return 1
    return 0


def main(argv=None):
    """
    Python hook for starting spanner from the command line.
    @param argv: standard argument vector
    """
    return _main(argv, SpannerMain)
