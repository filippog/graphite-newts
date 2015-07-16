graphite-newts
==============

A storage finger for [graphite-api](https://github.com/brutasse/graphite-api)
backed by [newts](http://opennms.github.io/newts/).

installation
------------
You will need newts and cassandra running somewhere on your network, for example `localhost`.

`graphite-api` is a WSGI application, to start a development server:

    virtualenv venv
    venv/bin/python setup.py install

You'll need also a build environment for cffi, thus:

    apt-get install build-environment python-dev libcffi-dev

Underneath you'll need a `newts` server running on `localhost:8080`, you can
follow the instructions on [how to get started with newts](https://github.com/OpenNMS/newts/wiki/GettingStarted).

You can spawn a demo `graphite-api` server on port `8888` with:

    venv/bin/graphite-newts --config graphite-api.yaml --port 8888

However for production deployments it is recommended to run `graphite-api` on a
real `WSGI` server.
