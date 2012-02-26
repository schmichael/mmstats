import sys

from setuptools import setup
from setuptools.extension import Extension

#XXX gettid only works on Linux, don't bother else
if 'linux' in sys.platform:
    exts = [Extension('mmstats._libgettid', sources=['mmstats/_libgettid.c'])]
else:
    exts = []

requirements = ['Flask']

try:
    import argparse
except ImportError:
    # We're probably on Python <2.7, add argparse as a requirement
    requirements.append('argparse')

setup(
    name='mmstats',
    url='https://github.com/schmichael/mmstats',
    version='0.5.0',
    license='BSD',
    author='Michael Schurter',
    author_email='m@schmichael.com',
    description='Stat, metric, and diagnostic publishing and consuming tools',
    long_description=open('README.rst').read(),
    packages=['mmstats'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'mmash=mmstats.mmash:main',
            'slurpstats=mmstats.slurpstats:main',
            'pollstats=mmstats.pollstats:main',
            'cleanstats=mmstats.clean:cli',
        ],
    },
    ext_modules=exts,
    test_suite='tests',
    install_requires=requirements,
    classifiers=['License :: OSI Approved :: BSD License'],
    # It might actually be zip-safe, I just hate eggs. File an issue or pull
    # request if mmstats is actually zip_safe and you care
    zip_safe=False
)
