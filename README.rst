MicroFS
-------

A community fork of uflash. PR welcome!

A simple command line tool and module for interacting with the limited
file system provided by MicroPython on the BBC micro:bit.

Installation
++++++++++++

Download the source code and install the package using the following command::

    $ pip install .

Usage
+++++

There are two ways to use microfs - as a module in your Python code or as a
stand-alone command to use from your shell (``ufs``).

In Code
=======

In your Python script import the required functions like this::

    from microfs import ls, rm, put, get, version, get_serial

Read the API documentation below to learn how each of the functions works.

Command Line
============

From the command line (but not the Python shell) use the "ufs" ("u" = micro)
command.

To read the built-in help::

    $ ufs --help

List the files on the device::

    $ ufs ls

You can also specify a delimiter to separte file names displayed on the output (default is whitespace ' ')::

    # use ';' as a delimiter
    $ ufs ls ';'

Delete a file on the device::

    $ ufs rm foo.txt

Copy a file onto the device::

    $ ufs put path/to/local.txt

Get a file from the device::

    $ ufs get remote.txt

The ``put`` and ``get`` commands optionally take a further argument to specify
the name of the target file::

    $ ufs put /path/to/local.txt remote.txt
    $ ufs get remote.txt local.txt

Development
+++++++++++

The source code is hosted in GitHub. Please feel free to fork the repository.
Assuming you have Git installed you can download the code from the canonical
repository with the following command::

    $ git clone https://github.com/blackteahamburger/microfs.git

To locally install your development version of the module into a virtualenv,
run the following command::

    $ pip install -e ".[dev]"

This also ensures that you have the correct dependencies for development.

There is a Makefile that helps with most of the common workflows associated with development.
