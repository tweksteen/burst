#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name = 'burst',
    version = '0.6',
    packages = ['burst'],
    scripts = ['bin/burst'],
    package_data = {'burst': [ 'payloads/*',]},
    description = 'Burst: interactive HTTP(S) tool/framework',
    url = "https://github.com/tweksteen/burst",
    author = u'Thiébaud Weksteen',
    author_email = "thiebaud@weksteen.fr",
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP"
        ],
)
