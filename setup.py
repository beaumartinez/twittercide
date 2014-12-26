#! /usr/bin/env python

from setuptools import find_packages
from setuptools import setup


with open('README.md') as readme_file:
    readme = readme_file.read()


setup(
    author='Beau Martinez',
    classifiers=[
        'Programming Language :: Python :: 2.7',
    ],
    description='Delete your tweets and backup tweeted photos to Google Drive.',
    entry_points={
        'console_scripts': [
            'twittercide = twittercide.__main__:main',
        ],
    },
    install_requires=[
        'arrow==0.4.4',
        'python-dateutil>=2.3',
        'requests-foauth>=0.1.1',
        'requests>=2.5.0',
    ],
    licence='ISC',
    long_description=readme,
    name='twittercide',
    packages=find_packages(),
    url='http://github.com/beaumartinez/twittercide',
    version='0.1',
)
