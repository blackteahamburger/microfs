Release History
===============

1.5.0
-----

* When reading a file, byte strings can use single and double quotes.
* Support for `--timeout` command line parameter and default value of timeout is adjusted to 10.
* Support for `--version` flag and a `version` subcommand.
* **API CHANGE**: Exception handling is now more granular. Introduced `MicroBitError`, `MicroBitIOError`, and `MicroBitNotFoundError` for micro:bit-specific errors, replacing generic `IOError` usage.
* **API CHANGE**: The `put` and `get` functions now use `pathlib.Path` objects for local file arguments (`filename` and `target`), instead of plain strings.
* **API CHANGE**: The `execute` function now returns only the stdout bytes (previously returned a tuple of (stdout, stderr)). Errors are now raised as exceptions instead of being returned.
* **API CHANGE**: The `put` and `get` command-line interfaces now require `pathlib.Path` objects for file arguments.

1.4.5
-----

* Updated version of PySerial used by the script.
* Non-zero exit codes when things go wrong.
* Execute as ``__main__``.
* Black formatting updates.
* Thanks to @carlosperate for these updates.

1.4.4
-----

* New feature. Thanks to @makinteract, it is possible to add an optional
  delimeter for the ``ls`` command. Please see PR #28 for more details.

1.4.3
-----

* Bug fix. See commentary in issue #22. Thanks again to alexandros769.

1.4.2
-----

* Update getting of data from micro:bit device to deal with control characters
  found within the file on the device. Thanks to Damien George for the fix and
  to GitHub user alexandros769 for reporting it.

1.4.1
-----

* Clamp PySerial version to use with microfs to a version known to work.

1.4.0
-----

* Updated and changed the ``get`` functionality to work on a wider range of
  supported boards. Many thanks to Carlos Pereira Atencio for putting in the
  effort to make this happen.

1.3.1
-----

* Fix bug in version parsing that was mangling the ``machine`` attribute.

1.3.0
-----

* Added a new function (not available via the command line) to get the version
  of MicroPython on the device.
* **API CHANGE** The find_microbit function now returns a tuple with position 0
  as the port and position 1 as the serial number of the connected device.

1.2.3
-----

* Extensive debugging and a fix by Carlos Pereira Atencio to ensure that serial
  connections are opened, closed and made ready for microfs related commands in
  a robust manner.

1.2.2
-----

* The get and put commands optionally take a further argument to specify the
  name of the target file.

1.2.1
-----

* Made implicit string concatenation explicit.

1.2.0
-----

* **API CHANGE** the serial object passed into command functions is optional.
* **API CHANGE** call signature changes on command functions.

1.1.2
-----

* Allow external modules to use built-in device detection and connection.

1.1.1
-----

* Unlink command logic from device detection and serial connection.

1.1.0
-----

* Fix broken 'put' and 'get' commands to work with arbitrary file sizes.
* Fix error when working with binary data.
* Update execute function to work with lists of multiple commands.
* Minor refactor to extract raw mode related code.
* Updated tests to keep coverage at 100% on both Python 2 and Python 3.

1.0.2
-----

* Remove spare print call.

1.0.1
-----

* Fix broken setup.

1.0.0
-----

* Full implementation of all the expected features.
* 100% test coverage.
* Comprehensive documentation.

0.0.1
-----

* Initial release. Basic functionality.
