from setuptools import setup
from setuptools.extension import Extension

libgettid = Extension('libgettid', sources=['libgettid.c'])

setup(
    name='mmstats',
    version='0.1',
    license='BSD',
    author='Michael Schurter',
    author_email='m@schmichael.com',
    description='Stat publishing and consuming tools',
    py_modules=['mmstats', 'slurpstats', 'mmash', 'mmash_settings'],
    ext_modules=[libgettid],
    install_requires=['Flask'],
    classifiers=['License :: OSI Approved :: BSD License'],
    zip_safe=False,
)
