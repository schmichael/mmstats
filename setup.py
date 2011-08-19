from setuptools import setup

setup(
    name='mmstats',
    version='0.1',
    license='BSD',
    author='Michael Schurter',
    author_email='m@schmichael.com',
    description='Stat publishing and consuming tools',
    py_modules=['mmstats', 'slurpmmstats', 'mmash', 'mmash_settings'],
    install_requires=['Flask'],
    classifiers=['License :: OSI Approved :: BSD License'],
)
