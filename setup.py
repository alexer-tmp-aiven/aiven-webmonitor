#! /usr/bin/env python
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

setup(
	name = 'webmonitor',
	version = '0.1',
	description = 'Web Monitor',
	author = 'Aleksi Torhamo',
	author_email = 'aleksi@torhamo.net',
	packages = ['webmonitor'],
)

