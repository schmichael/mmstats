import sys

from setuptools import setup
from setuptools.extension import Extension

#XXX gettid only works on Linux, don't bother else
if 'linux' in sys.platform:
    exts = [Extension('_libgettid', sources=['_libgettid.c'])]
else:
    exts = []

setup(
    name='mmstats',
    version='0.3.2',
    license='BSD',
    author='Michael Schurter',
    author_email='m@schmichael.com',
    description='Stat publishing and consuming tools',
    py_modules=['libgettid',
                'mmstats',
                'slurpstats',
                'mmash',
                'mmash_settings'
            ],
    ext_modules=exts,
    install_requires=['Flask'],
    classifiers=['License :: OSI Approved :: BSD License'],
    zip_safe=False,
)
