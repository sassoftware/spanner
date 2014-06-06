#!/usr/bin/python
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


from conary.cmds import updatecmd
from conary import conarycfg
from conary import conaryclient
from conary.conaryclient import cml
from conary.conaryclient import systemmodel


import logging

logger = logging.getLogger(__name__)


class ConaryClientFactory(object):
    def getClient(self, modelFile=None, model=False):
        ccfg = self.getCfg()
        if model:
            if not modelFile:
                model = cml.CML(ccfg)
                modelFile = systemmodel.SystemModelFile(model)
            cclient = conaryclient.ConaryClient(ccfg, modelFile=modelFile)
        else:
            cclient = conaryclient.ConaryClient(ccfg)
        callback = updatecmd.callbacks.UpdateCallback()
        cclient.setUpdateCallback(callback)
        return cclient

    def getCfg(self, readconfig=True, initflv=True):
        ccfg = conarycfg.ConaryConfiguration(readConfigFiles=readconfig)
        if initflv:
            ccfg.initializeFlavors()
        return ccfg
