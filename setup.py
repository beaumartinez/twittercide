#! /usr/bin/env python

from setuptools import find_packages
from setuptools import setup


with open('README.md') as readme_file:
    readme = readme_file.read()


setup(
    author='Beau Martinez',
    author_email='beau@beaumartinez.com',
    classifiers=[
        'Programming Language :: Python :: 2.7',
    ],
    description='Delete your tweets and backup tweeted photos to Google Drive.',
    install_requires=[
        'arrow==0.4.4',
        'python-dateutil>=2.3',
        'requests-foauth>=0.1.1',
        'requests>=2.5.0',
    ],
    licence='WTFPL',
    long_description=readme,
    name='twittercide',
    packages=find_packages(),
    scripts=[
        'twittercide.py',
    ],
    url='http://github.com/beaumartinez/twittercide',
    version='0.1',
)
