# tenjint - VMI Python Library
#
# Copyright (C) 2020 Bedrock Systems, Inc
# Authors: Jonas Pfoh <jonas@bedrocksystems.com>
#          Sebastian Vogl <sebastian@bedrocksystems.com>
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

import setuptools
import platform
from Cython.Build import cythonize

extensions = [
    setuptools.extension.Extension(
        "tenjint.api.tenjintapi",
        ["tenjint/api/tenjintapi.pyx"],
        include_dirs=[
            "../qemu/include/",
            "../qemu/linux-headers/"
        ],
        language="c"
    )]

if platform.machine() == "x86_64":
    extensions.append(
        setuptools.extension.Extension(
            "tenjint.api.tenjintapi_x86_64",
            ["tenjint/api/tenjintapi_x86_64.pyx"],
            include_dirs=[
                "../qemu/",
                "../qemu/include/",
                "../qemu/linux-headers/",
                "../qemu/target/",
                "../qemu/target/i386/",
                "../qemu/tcg/",
                "../qemu/x86_64-softmmu/",
                "../qemu/tcg/i386/",
                "/usr/include/glib-2.0/",
                "/usr/lib/x86_64-linux-gnu/glib-2.0/include/"
            ],
            extra_compile_args=[
                "-DNEED_CPU_H"
            ],
            undef_macros = [ "NDEBUG" ],
            language="c"
        ))
elif platform.machine() == "aarch64":
    extensions.append(
        setuptools.extension.Extension(
            "tenjint.api.tenjintapi_aarch64",
            ["tenjint/api/tenjintapi_aarch64.pyx"],
            include_dirs=[
                "../qemu/",
                "../qemu/include/",
                "../qemu/linux-headers/",
                "../qemu/target/",
                "../qemu/target/arm/",
                "../qemu/tcg/",
                "../qemu/aarch64-softmmu/",
                "../qemu/tcg/aarch64/",
                "/usr/include/glib-2.0/",
                "/usr/lib/aarch64-linux-gnu/glib-2.0/include/"
            ],
            extra_compile_args=[
                "-DNEED_CPU_H"
            ],
            undef_macros = [ "NDEBUG" ],
            language="c"
        ))
else:
    raise RuntimeError("Unsupported Architecture: {}".format(platform.machine()))

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tenjint",
    version="0.0.1",
    author="Jonas Pfoh, Sebastian Vogl",
    author_email="jonas@bedrocksystems.com, sebastian@bedrocksystems.com",
    description="This is a VMI library that runs within QEMU as part of tenjint.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/bedrocksystems/introspection/tenjint",
    packages=setuptools.find_packages(),
    ext_modules = cythonize(extensions),
    install_requires = [
        'Cython',
        'six',
        'tblib',
        'numpy',
        'sphinx',
        'sphinx_rtd_theme'
    ]
)
