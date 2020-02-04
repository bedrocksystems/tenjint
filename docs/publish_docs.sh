#!/bin/bash

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

# Clean
rm -rf generated
rm -rf _build

# build
python3 generate_api_rst.py
mkdir _build
sphinx-build -b html . _build/html

# publish.
mkdir /tmp/tenjint-new-doc
cp -r _build/html/* /tmp/tenjint-new-doc
git clone git@github.com:bedrocksystems/tenjint.git /tmp/tenjint-doc
cd /tmp/tenjint-doc
git branch -D gh-pages
git checkout -b gh-pages
rm -rf *
cp -r /tmp/tenjint-new-doc/* .
touch .nojekyll
git add *
git add .nojekyll
git commit -a -m "documentation update"
git push --force origin gh-pages
rm -rf /tmp/tenjint-*
cd -
