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
