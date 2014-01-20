#-*- coding: utf-8 -*-
import os, sys
from setuptools import setup

setup(
    name='duplicates',
    version='0.2',
    description='Fast File-Level Deduplicator',
    long_description="""Duplicates use a fast algorithm, to early reject false positives.

A file is compared to others files, by using, in order:
 - size
 - hash of first KB
 - hash of content

This program uses temporary files and external "sort" to minimise memory
utilization.
""",
    author='Gautier Portet',
    author_email='kassoulet@gmail.com',
    zip_safe=True,
    license='GNU General Public License v3 (GPL)',
    url='http://',
    scripts = [
        'duplicates.py'
    ],
    classifiers = [
              'Programming Language :: Python :: 3',
              'Development Status :: 4 - Beta',
              'Operating System :: POSIX'
              'Topic :: System :: Archiving'
              'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
           ],
)

