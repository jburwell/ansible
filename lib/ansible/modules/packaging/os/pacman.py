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

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: pacman
short_description: Manage packages with I(pacman)
description:
    - Manage packages with the I(pacman) package manager, which is used by
      Arch Linux and its variants.
version_added: "1.0"
author:
    - "Indrajit Raychaudhuri (@indrajitr)"
    - "'Aaron Bull Schaefer (@elasticdog)' <aaron@elasticdog.com>"
    - "Afterburn"
notes: []
requirements: []
options:
    name:
        description:
            - Name of the package to install, upgrade, or remove.
        required: false
        default: null
        aliases: [ 'pkg', 'package' ]

    state:
        description:
            - Desired state of the package.
        required: false
        default: "present"
        choices: ["present", "absent", "latest"]

    recurse:
        description:
            - When removing a package, also remove its dependencies, provided
              that they are not required by other packages and were not
              explicitly installed by a user.
        required: false
        default: no
        choices: ["yes", "no"]
        version_added: "1.3"

    force:
        description:
            - When removing package - force remove package, without any
              checks. When update_cache - force redownload repo
              databases.
        required: false
        default: no
        choices: ["yes", "no"]
        version_added: "2.0"

    update_cache:
        description:
            - Whether or not to refresh the master package lists. This can be
              run as part of a package installation or as a separate step.
        required: false
        default: no
        choices: ["yes", "no"]
        aliases: [ 'update-cache' ]

    upgrade:
        description:
            - Whether or not to upgrade whole system
        required: false
        default: no
        choices: ["yes", "no"]
        version_added: "2.0"
'''

RETURN = '''
packages:
    description: a list of packages that have been changed
    returned: when upgrade is set to yes
    type: list of strings
    sample: ['package', 'other-package']
'''

EXAMPLES = '''
# Install package foo
- pacman:
    name: foo
    state: present

# Upgrade package foo
- pacman:
    name: foo
    state: latest
    update_cache: yes

# Remove packages foo and bar
- pacman:
    name: foo,bar
    state: absent

# Recursively remove package baz
- pacman:
    name: baz
    state: absent
    recurse: yes

# Run the equivalent of "pacman -Sy" as a separate step
- pacman:
    update_cache: yes

# Run the equivalent of "pacman -Su" as a separate step
- pacman:
    upgrade: yes

# Run the equivalent of "pacman -Syu" as a separate step
- pacman:
    update_cache: yes
    upgrade: yes

# Run the equivalent of "pacman -Rdd", force remove package baz
- pacman:
    name: baz
    state: absent
    force: yes
'''

from ansible.module_utils.arch_linux_common import PacmanModule


def main():
    module = PacmanModule("pacman")
    module.main()


if __name__ == "__main__":
    main()
