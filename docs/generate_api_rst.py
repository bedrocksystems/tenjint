#!/usr/bin/python3

# tenjint - VMI Python Library
# Document Generation
#
# Copyright (C) 2020 Bedrock Systems, Inc
# Authors: Sebastian Vogl <sebastian@bedrocksystems.com>
#          Jonas Pfoh <jonas@bedrocksystems.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Generate the api.rst file by extracting all tenjint modules."""

from os import walk
import os.path

template = """
API Reference
=============

.. rubric:: Modules

.. autosummary::
   :toctree: generated

"""

# Get python files
py = []
for (dirpath, dirnames, filenames) in walk("../tenjint/"):
    for f in filenames:
        if "__" in f:
            continue
        if ".pyc" in f:
            continue
        py.append(os.path.join(dirpath, f))

# Generate template
with open("api.rst", "w") as f:
    f.write(template)

    for pyf in py:
        line, _ = os.path.splitext(pyf)
        # remove ../
        line = line[3:]
        # Convert to module
        line = line.replace("/", ".")
        f.write("   {}\n".format(line))

