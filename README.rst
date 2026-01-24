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

In your Python script import the required functions like this::

    from microfs.lib import MicroBitSerial, ls, rm, cp, mv, cat, du, put, get, version, micropython_version

Read the API documentation below to learn how each of the functions works.

Command Line
^^^^^^^^^^^^

From the command line use the ``ufs``/``microfs`` command.

To read the built-in help::

    $ ufs --help

To see the version of microfs::

    $ ufs --version

To set the device timeout (default is 10 seconds)::

    $ ufs --timeout 3 command

List the files on the device::

    $ ufs ls

You can also specify a delimiter to separate file names displayed on the output
(default is whitespace ' ')::

    # use ';' as a delimiter
    $ ufs ls ';'

Delete a file on the device::

    $ ufs rm foo.txt

Copy a file from one location to another on the device::

    $ ufs cp foo.txt bar.txt

Move a file from one location to another on the device::

    $ ufs mv foo.txt bar.txt

Display the contents of a file on the device::

    $ ufs cat foo.txt

Get the size of a file on the device in bytes::

    $ ufs du foo.txt

Copy a file onto the device::

    $ ufs put path/to/local.txt

Get a file from the device::

    $ ufs get remote.txt

The ``put`` and ``get`` commands optionally take a further argument to specify
the name of the target file::

    $ ufs put /path/to/local.txt remote.txt
    $ ufs get remote.txt local.txt

Get information identifying the current operating system on the device::

    $ ufs version

To show MicroPython version information only::

    $ ufs version --micropython
