#!/usr/bin/python


# Test suite for gitbuilder


import os
import subprocess
from git import GitRepository as gitme
import time
import config
import gitbuilder


def write_file(path, data):
    try:
        f = open(path, 'w')
        f.write(str(str(data)))
    except Exception, e:
        raise
    return


def runcmd(self, cmd, directory=None):
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, cwd=directory)
    stdout, _ = p.communicate()
    if p.returncode:
        raise RuntimeError("%s exited with status %s" % (cmd[0], p.returncode))
    return stdout


def setup(testdir, testrepo):
    '''
    mkdir test
    cd test/
    git init
    echo "Main Origin" > README
    echo $(date) >> README
    cat bobplantest >> bobtestplan.bob
    git add README
    git commit -m "Initial README"
    git branch 1.0
    git commit -m "Branch 1.0"
    git checkout 1.0
    echo "Branch 1.0" > README
    echo $(date) >> README
    sed -i 's/gituri/newgituri/g' bobplan
    git commit -m "Changes to Branch 1.0"
    '''

    if not os.path.exists(testdir):
        os.makedirs(testdir)
    os.chdir(testdir)
    ret = git.createRepo(testrepo)
    readme = '''Main Origin\n%s\n''' % time.time()
    write_file('README', readme)
    bobtestplan = '''resolveTroves []
resolveTroves group-rpath-packages=%(common_label)s
resolveTroves group-os=%(distro_label)s
macros version 0
installLabelpath %(common_label)s
scm sasinside-utilities-webminmaster git git://paasstudio.unx.sas.com/utilities.webminmaster.git
target []
target sasinside-utilities-webminmaster
[target:sasinside-utilities-webminmaster]
version %(version)s.%(git)s
scm sasinside-utilities-webminmaster
flavor_set x86_64
sourceTree sasinside-utilities-webminmaster recipes/
    '''
    write_file('bobtestplan.bob', bobtestplan)
    git.add('README')
    git.add('bobtestplan.bob')
    git.commit('Initial commit to repository')
    git.branch('1.0')
    git.commit('Branch 1.0')
    git.checkoutBranch('1.0')
    readme = '''Branch 1.0\n%s\n''' % time.time()
    write_file('README', readme)
    bobtestplan = '''resolveTroves []
resolveTroves group-rpath-packages=%(common_label)s
resolveTroves group-os=%(distro_label)s
macros version 0
installLabelpath %(common_label)s
scm sasinside-utilities-webminmaster git git://paasstudio.unx.sas.com/utilities.webminmaster.git
target []
target sasinside-utilities-webminmaster
[target:sasinside-utilities-webminmaster]
version %(version)s.%(git)s
scm sasinside-utilities-webminmaster
flavor_set x86_64
sourceTree sasinside-utilities-webminmaster recipes/
    '''
    write_file('bobtestplan.bob', bobtestplan)
    git.commit()

    # setup repo using git.py
    # create fake repo using testutils
    # verify
    pass


def test():
    # read bobplan for head
    # read bobplan for branch
    # build pkgs for head
    # build pkgs for branch
    # commit changes to repo
    # determine pkg changes vs label
    # skip one for no change
    # run build again for change
    pass
