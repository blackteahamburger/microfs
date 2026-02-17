MicroFS
=======

A community fork of `MicroFS <https://github.com/ntoll/microfs>`_.

A simple command line tool and module for interacting with the limited
file system provided by MicroPython on the BBC micro:bit.

Installation
------------

To install simply type::

    $ pip install microfs2

Usage
-----

There are two ways to use microfs - as a module in your Python code or as a
stand-alone command to use from your shell (``ufs``/``microfs``).

In Code
^^^^^^^

Read the API documentation to learn how each of the class & functions works.

Command Line
^^^^^^^^^^^^

From the command line use the ``ufs``/``microfs`` command.

To read the built-in help::

    $ ufs --help

To read the help for a specific subcommand::

    $ ufs <subcommand> --help
