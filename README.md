graphite-newts
==============

A [graphite-api](https://github.com/brutasse/graphite-api) based storage finder
backed by [newts](http://opennms.github.io/newts/).

installation
------------
You will need newts and cassandra running somewhere on your network, for example `localhost`.

`graphite-api` is a WSGI application, to start a development server:

  virtualenv venv
  venv/bin/python setup.py install

You'll need also a build environment for cffi, thus:
  apt-get install python-dev libcffi-dev
