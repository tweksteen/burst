#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name = 'abrupt',
    version = '20110324',
    packages = ['abrupt'],
    scripts = ['bin/abrupt'],
    package_data = {'abrupt': ['cert/*', 'payloads/*']},
    description = 'Abrupt: interactive HTTP(S) tool',
    url = "https://github.com/tweksteen/abrupt",
    author = u'Thiébaud Weksteen',
    author_email = "tweksteen@gmail.com",
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License"
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP"
        ],
)
