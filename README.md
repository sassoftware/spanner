# README : Spanner

Spanner 
=======

About
--------

**Spanner** is a python program that leverages wms and git to enable continuous 
integration builds. Spanner automates building packages from  multiple git repos 
into conary packages as well as building conary groups after build runs.

Overview
---------

**Spanner** is a command line tool written in python to automate building packages 
from multiple git repos into conary packages consumable for vApps. **Spanner** 
leverages WMS and git to enable continuous integration builds. **Spanner** 
automates building packages from  multiple git repos into conary packages 
as well as building conary groups after build runs.

**Spanner** requires a **WMS** control repo with a directory of bob-plans. 

The bob-plans directory must contain specific directories.

Project/
    ├ ─ ─ control.yaml # Contains a list of git repos to add to your forest
    ├── bob-plans
        ├── config # Config files for bob.
        ├── external # Packages built outside spanner on conary label
        ├── products # Conary Groups
        └── projects # Conary Pkgs built by spanner

spanner also requires a wms url.

ie:   http://wheresmystuff.unx.sas.com/api/repos/gerrit-pdt/tools:build-tools

How it works
-------------

### High Level

**Spanner** uses a directory structure populated with config files and build 
plans for all the packages it intends to build. This directories are located 
in the control git repo of a git forest. This provides version control and 
branching. **Spanner** snapshots the control repo, reads the plan files, and 
creates a set of packages. The tool then iterates through the set and checks 
the git repo for its commit and compares it to the version of the package in 
the corresponding conary repo. If the commit and the version do not match 
spanner passes the package off to bob the builder to be built, setting the 
version to the commit revision of the git repo. Upon success spanner updates 
the package version in the set and proceeds to process. Once all the builds 
are finished spanner can build a group of the specific versions of all the 
packages in the build plans and include external packages not built by spanner 
with build plans located in the external directory.

Procedure

* Fetch Plans       - Snapshot the git control repo

* Read Plans        - Read the plans in the projects, products, external, 
                        and config directories

* Check Plans       - Check the git commit versions and the conary versions of 
                        the packages and set flag for build

* Build Packages    - Build all packages marked as changed

* Group Build       - [Optional] Build a group from all packages in the projects 
                        dir and optionally include packages from the external dir

* Product Build     - [Optional] Build plans located from the products dir.


### Common Reference

    -   build  Build all packages that have changed in the git forest.

    -   plan   Make a set of bob plan templates for a git forest.

    -   config Show spanner config

    -   OPTIONS

       --branch=BRANCH

              Specifies the branch to build. Defaults to master  if  not  sup-
              plied ie: --branch master

       --cfgfile=CFGFILE

              Specifies  a specific spannerrc. Defaults to none using internal
              hard coded config. Not required in most instances.   ie:  --cfg-
              file ~/spannerrc

       --debug-logging

              Toggles  debug log level on. Defaults to off (quiet) if not sup-
              plied. Provides useful output when run in jenkins.

       --dry-run

              Toggles test mode on. Defaults to off. Used on initial  runs  to
              test outputs. usually paired with --debug-logging

       --group

              Toggles  group  build  on. Defaults to off. When on spanner will
              create a group at the end of the  build  run.  The  contents  of
              which  include all packages in projects and optionally the pack-
              ages specified in external directories. Uses  a  special  config
              file group.conf in the config directory.


       --products

              Toggles  products build on. Defaults to off. Builds the plans in
              the products directory. Used for packages or group  builds  that
              require pkgs in projects to be built before building.

       --quiet

              Toggles silent mode. Defaults to off. Deprecated.


Credits
--------

* Credits -- Brett Smith <bc.smith@sas.com> 
* Copyright -- (c) SAS Institute Inc.
* License -- SEE LICENSE

