#!/usr/bin/python3

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

