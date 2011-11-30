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
    url='https://github.com/schmichael/mmstats',
    version='0.3.12',
    license='BSD',
    author='Michael Schurter',
    author_email='m@schmichael.com',
    description='Stat publishing and consuming tools',
    long_description=open('README.rst').read(),
    py_modules=['libgettid',
                'mmstats',
                'mmstats_compat',
                'pollstats',
                'slurpstats',
                'mmash',
                'mmash_settings'
            ],
    entry_points={
        'console_scripts': [
            'mmash=mmash:main',
            'slurpstats=slurpstats:main',
            'pollstats=pollstats:main',
        ],
    },
    ext_modules=exts,
    install_requires=['Flask'],
    classifiers=['License :: OSI Approved :: BSD License'],
    zip_safe=False,
)
