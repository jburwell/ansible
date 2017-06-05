#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

# (c) 2017, John Burwell <https://github.com/jburwell>

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

from __future__ import absolute_import

from ansible.modules.packaging.os.pacman import PacmanModule


def main():
    module = PacmanModule("yaourt")
    module.main()


if __name__ == "__main__":
    main()
