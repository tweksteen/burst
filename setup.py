#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name = 'abrupt',
    version = '0.3',
    packages = ['abrupt'],
    scripts = ['bin/abrupt'],
    package_data = {'abrupt': [ 'payloads/*',]},
    description = 'Abrupt: interactive HTTP(S) tool',
    url = "https://github.com/securusglobal/abrupt",
    author = u'Thiébaud Weksteen',
    author_email = "thiebaud.weksteen@securusglobal.com",
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
