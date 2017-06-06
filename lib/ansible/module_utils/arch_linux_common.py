#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

# (c) 2012, Afterburn <http://github.com/afterburn>
# (c) 2013, Aaron Bull Schaefer <aaron@elasticdog.com>
# (c) 2015, Indrajit Raychaudhuri <irc+code@indrajit.com>
# (c) 2-17, John Burwell <meaux@cockamamy.net>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import re

# import module snippets
from ansible.module_utils.basic import *


class PacmanModule(AnsibleModule):
    def __init__(self, module_name):
        super(PacmanModule, self).__init__(
            argument_spec=dict(
                name=dict(aliases=['pkg', 'package'], type='list'),
                state=dict(
                    default='present',
                    choices=[
                        'present', 'installed', "latest", 'absent', 'removed'
                    ]),
                recurse=dict(default=False, type='bool'),
                force=dict(default=False, type='bool'),
                upgrade=dict(default=False, type='bool'),
                update_cache=dict(
                    default=False, aliases=['update-cache'], type='bool')),
            required_one_of=[['name', 'update_cache', 'upgrade']],
            supports_check_mode=True)
        self._name = module_name
        self._bin_path = self.get_bin_path(module_name, True)

    def get_version(self, pacman_output):
        """Take pacman -Qi or pacman -Si output and get the Version"""
        lines = pacman_output.split('\n')
        for line in lines:
            if 'Version' in line:
                return line.split(':')[1].strip()
        return None

    def query_package(self, name, state="present"):
        """Query the package status in both the local system and the repository. Returns a boolean to indicate if the package is installed, a second
        boolean to indicate if the package is up-to-date and a third boolean to indicate whether online information were available
        """
        if state == "present":
            lcmd = "%s -Qi %s" % (self._bin_path, name)
            lrc, lstdout, lstderr = self.run_command(lcmd, check_rc=False)
            if lrc != 0:
                # package is not installed locally
                return False, False, False

            # get the version installed locally (if any)
            lversion = self.get_version(lstdout)

            rcmd = "%s -Si %s" % (self._bin_path, name)
            rrc, rstdout, rstderr = self.run_command(rcmd, check_rc=False)
            # get the version in the repository
            rversion = self.get_version(rstdout)

            if rrc == 0:
                # Return True to indicate that the package is installed locally, and the result of the version number comparison
                # to determine if the package is up-to-date.
                return True, (lversion == rversion), False

            # package is installed but cannot fetch remote Version. Last True stands for the error
            return True, True, True

    def update_package_db(self):
        if self.params["force"]:
            args = "Syy"
        else:
            args = "Sy"

        cmd = "%s -%s" % (self._bin_path, args)
        rc, stdout, stderr = self.run_command(cmd, check_rc=False)

        if rc == 0:
            return True
        else:
            self.fail_json(msg="could not update package db")

    def upgrade(self):
        cmdupgrade = "%s -Suq --noconfirm" % (self._bin_path)
        cmdneedrefresh = "%s -Qu" % (self._bin_path)
        rc, stdout, stderr = self.run_command(cmdneedrefresh, check_rc=False)
        data = stdout.split('\n')
        data.remove('')
        packages = []
        diff = {
            'before': '',
            'after': '',
        }

        if rc == 0:
            regex = re.compile(
                '([\w-]+) ((?:\S+)-(?:\S+)) -> ((?:\S+)-(?:\S+))')
            for p in data:
                m = regex.search(p)
                packages.append(m.group(1))
                if self._diff:
                    diff['before'] += "%s-%s\n" % (m.group(1), m.group(2))
                    diff['after'] += "%s-%s\n" % (m.group(1), m.group(3))
            if self.check_mode:
                self.exit_json(
                    changed=True,
                    msg="%s package(s) would be upgraded" % (len(data)),
                    packages=packages,
                    diff=diff)
            rc, stdout, stderr = self.run_command(cmdupgrade, check_rc=False)
            if rc == 0:
                self.exit_json(
                    changed=True,
                    msg='System upgraded',
                    packages=packages,
                    diff=diff)
            else:
                self.fail_json(msg="Could not upgrade")
        else:
            self.exit_json(
                changed=False, msg='Nothing to upgrade', packages=packages)

    def remove_packages(self, packages):
        data = []
        diff = {
            'before': '',
            'after': '',
        }

        if self.params["recurse"] or self.params["force"]:
            if self.params["recurse"]:
                args = "Rs"
            if self.params["force"]:
                args = "Rdd"
            if self.params["recurse"] and self.params["force"]:
                args = "Rdds"
        else:
            args = "R"

        remove_c = 0
        # Using a for loop in case of error, we can report the package that failed
        for package in packages:
            # Query the package first, to see if we even need to remove
            installed, updated, unknown = self.query_package(package)

            if not installed:
                continue

            cmd = "%s -%s %s --noconfirm --noprogressbar" % (self._bin_path,
                                                             args, package)
            rc, stdout, stderr = self.run_command(cmd, check_rc=False)

            if rc != 0:
                self.fail_json(msg="failed to remove %s" % (package))

            if self._diff:
                d = stdout.split('\n')[2].split(' ')[2:]
                for i, pkg in enumerate(d):
                    d[i] = re.sub('-[0-9].*$', '', d[i].split('/')[-1])
                    diff['before'] += "%s\n" % pkg
                data.append('\n'.join(d))

            remove_c += 1

        if remove_c > 0:
            self.exit_json(
                changed=True,
                msg="removed %s package(s)" % remove_c,
                diff=diff)

        self.exit_json(changed=False, msg="package(s) already absent")

    def install_packages(self, state, packages, package_files):
        install_c = 0
        package_err = []
        message = ""
        data = []
        diff = {
            'before': '',
            'after': '',
        }

        to_install_repos = []
        to_install_files = []
        for i, package in enumerate(packages):
            # if the package is installed and state == present or state == latest and is up-to-date then skip
            installed, updated, latestError = self.query_package(package)
            if latestError and state == 'latest':
                package_err.append(package)

            if installed and (state == 'present' or
                              (state == 'latest' and updated)):
                continue

            if package_files[i]:
                to_install_files.append(package_files[i])
            else:
                to_install_repos.append(package)

        if to_install_repos:
            cmd = "%s -S %s --noconfirm --noprogressbar --needed" % (
                self._bin_path, " ".join(to_install_repos))
            rc, stdout, stderr = self.run_command(cmd, check_rc=False)

            if rc != 0:
                self.fail_json(msg="failed to install %s: %s" %
                               (" ".join(to_install_repos), stderr))

            data = stdout.split('\n')[3].split(' ')[2:]
            data = [i for i in data if i != '']
            for i, pkg in enumerate(data):
                data[i] = re.sub('-[0-9].*$', '', data[i].split('/')[-1])
                if self._diff:
                    diff['after'] += "%s\n" % pkg

            install_c += len(to_install_repos)

        if to_install_files:
            cmd = "%s -U %s --noconfirm --noprogressbar --needed" % (
                self._bin_path, " ".join(to_install_files))
            rc, stdout, stderr = self.run_command(cmd, check_rc=False)

            if rc != 0:
                self.fail_json(msg="failed to install %s: %s" %
                               (" ".join(to_install_files), stderr))

            data = stdout.split('\n')[3].split(' ')[2:]
            data = [i for i in data if i != '']
            for i, pkg in enumerate(data):
                data[i] = re.sub('-[0-9].*$', '', data[i].split('/')[-1])
                if self._diff:
                    diff['after'] += "%s\n" % pkg

            install_c += len(to_install_files)

        if state == 'latest' and len(package_err) > 0:
            message = "But could not ensure 'latest' state for %s package(s) as remote version could not be fetched." % (
                package_err)

        if install_c > 0:
            self.exit_json(
                changed=True,
                msg="installed %s package(s). %s" % (install_c, message),
                diff=diff)

        self.exit_json(
            changed=False,
            msg="package(s) already installed. %s" % (message),
            diff=diff)

    def check_packages(self, packages, state):
        would_be_changed = []
        diff = {
            'before': '',
            'after': '',
            'before_header': '',
            'after_header': ''
        }

        for package in packages:
            installed, updated, unknown = self.query_package(package)
            if ((state in ["present", "latest"] and not installed) or
                (state == "absent" and installed) or
                (state == "latest" and not updated)):
                would_be_changed.append(package)
        if would_be_changed:
            if state == "absent":
                state = "removed"

            if self._diff and (state == 'removed'):
                diff['before_header'] = 'removed'
                diff['before'] = '\n'.join(would_be_changed) + '\n'
            elif self._diff and ((state == 'present') or (state == 'latest')):
                diff['after_header'] = 'installed'
                diff['after'] = '\n'.join(would_be_changed) + '\n'

            self.exit_json(
                changed=True,
                msg="%s package(s) would be %s" % (len(would_be_changed),
                                                   state),
                diff=diff)
        else:
            self.exit_json(
                changed=False, msg="package(s) already %s" % state, diff=diff)

    def expand_package_groups(self, pkgs):
        expanded = []

        for pkg in pkgs:
            cmd = "%s -Sgq %s" % (self._bin_path, pkg)
            rc, stdout, stderr = self.run_command(cmd, check_rc=False)

            if rc == 0:
                # A group was found matching the name, so expand it
                for name in stdout.split('\n'):
                    name = name.strip()
                    if name:
                        expanded.append(name)
            else:
                expanded.append(pkg)

        return expanded

    def main(self):
        p = self.params

        # normalize the state parameter
        if p['state'] in ['present', 'installed']:
            p['state'] = 'present'
        elif p['state'] in ['absent', 'removed']:
            p['state'] = 'absent'

        if p["update_cache"] and not self.check_mode:
            self.update_package_db()
            if not (p['name'] or p['upgrade']):
                self.exit_json(
                    changed=True, msg='Updated the package master lists')

        if p['update_cache'] and self.check_mode and not (p['name'] or
                                                          p['upgrade']):
            self.exit_json(
                changed=True, msg='Would have updated the package cache')

        if p['upgrade']:
            self.upgrade()

        if p['name']:
            pkgs = self.expand_package_groups(p['name'])

            pkg_files = []
            for i, pkg in enumerate(pkgs):
                if re.match(".*\.pkg\.tar(\.(gz|bz2|xz|lrz|lzo|Z))?$", pkg):
                    # The package given is a filename, extract the raw pkg name from
                    # it and store the filename
                    pkg_files.append(pkg)
                    pkgs[i] = re.sub('-[0-9].*$', '', pkgs[i].split('/')[-1])
                else:
                    pkg_files.append(None)

            if self.check_mode:
                self.check_packages(pkgs, p['state'])

            if p['state'] in ['present', 'latest']:
                self.install_packages(p['state'], pkgs, pkg_files)
            elif p['state'] == 'absent':
                self.remove_packages(pkgs)
