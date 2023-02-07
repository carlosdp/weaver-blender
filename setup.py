#!/usr/bin/env python

from distutils.core import setup

setup(name='weaver_blender',
      version='0.1',
      description='Blender renderer for Weaver',
      author='Carlos Diaz-Padron',
      packages=['weaver_blender'],
      install_requires=['runpod', 'requests', 'sentry-sdk'],
      )
