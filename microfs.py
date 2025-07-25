# -*- coding: utf-8 -*-
"""
This module contains functions for running remote commands on the BBC micro:bit
relating to file system based operations.

You may:

* ls - list files on the device. Based on the equivalent Unix command.
* rm - remove a named file on the device. Based on the Unix command.
* put - copy a named local file onto the device a la equivalent FTP command.
* get - copy a named file from the device to the local file system a la FTP.
"""

from __future__ import print_function

import argparse
import ast
import os
import os.path
import sys
import time
from typing import Literal

from serial import Serial
from serial.tools.list_ports import comports as list_serial_ports

__all__ = ["ls", "rm", "put", "get", "get_serial"]


#: The help text to be shown when requested.
_HELP_TEXT = """
Interact with the basic filesystem on a connected BBC micro:bit device.
You may use the following commands:

'ls' - list files on the device (based on the equivalent Unix command);
'rm' - remove a named file on the device (based on the Unix command);
'put' - copy a named local file onto the device just like the FTP command; and,
'get' - copy a named file from the device to the local file system a la FTP.

For example, 'ufs ls' will list the files on a connected BBC micro:bit.
"""

#: MAJOR, MINOR, RELEASE, STATUS [alpha, beta, final], VERSION
_VERSION = "1.4.6"

command_line_flag = False  # Indicates running from the command line.
SERIAL_BAUD_RATE = 115200


def find_microbit() -> tuple[str, str | None] | tuple[None, None]:
    """
    Returns a tuple representation of the port and serial number for a
    connected micro:bit device. If no device is connected the tuple will be
    (None, None).
    """
    ports = list_serial_ports()
    for port in ports:
        if "VID:PID=0D28:0204" in port[2].upper():
            return (port[0], port.serial_number)
    return (None, None)


def raw_on(serial: Serial) -> None:
    """
    Puts the device into raw mode.
    """

    def flush_to_msg(serial: Serial, msg: bytes) -> None:
        """
        Read the rx serial data until we reach an expected message.
        """
        data = serial.read_until(msg)
        if not data.endswith(msg):
            if command_line_flag:
                print(data)
            raise IOError("Could not enter raw REPL.")

    def flush(serial: Serial) -> None:
        """
        Flush all rx input without relying on serial.flushInput().
        """
        n = serial.in_waiting
        while n > 0:
            serial.read(n)
            n = serial.in_waiting

    raw_repl_msg = b"raw REPL; CTRL-B to exit\r\n>"
    # Send CTRL-B to end raw mode if required.
    serial.write(b"\x02")
    # Send CTRL-C three times between pauses to break out of loop.
    for _ in range(3):
        serial.write(b"\r\x03")
        time.sleep(0.01)
    flush(serial)
    # Go into raw mode with CTRL-A.
    serial.write(b"\r\x01")
    flush_to_msg(serial, raw_repl_msg)
    # Soft Reset with CTRL-D
    serial.write(b"\x04")
    flush_to_msg(serial, b"soft reboot\r\n")
    # Some MicroPython versions/ports/forks provide a different message after
    # a Soft Reset, check if we are in raw REPL, if not send a CTRL-A again
    data = serial.read_until(raw_repl_msg)
    if not data.endswith(raw_repl_msg):
        serial.write(b"\r\x01")
        flush_to_msg(serial, raw_repl_msg)
    flush(serial)


def raw_off(serial: Serial) -> None:
    """
    Takes the device out of raw mode.
    """
    serial.write(b"\x02")  # Send CTRL-B to get out of raw mode.


def get_serial(timeout: int = 10) -> Serial:
    """
    Detect if a micro:bit is connected and return a serial object to talk to
    it.
    """
    port, _serial_number = find_microbit()
    if port is None:
        raise IOError("Could not find micro:bit.")
    return Serial(port, SERIAL_BAUD_RATE, timeout=10, parity="N")


def execute(
    commands: list[str], serial: Serial | None = None, timeout: int = 10
) -> tuple[Literal[b""], bytes] | tuple[bytes, Literal[b""]]:
    """
    Sends the command to the connected micro:bit via serial and returns the
    result. If no serial connection is provided, attempts to autodetect the
    device.

    For this to work correctly, a particular sequence of commands needs to be
    sent to put the device into a good state to process the incoming command.

    Returns the stdout and stderr output from the micro:bit.
    """
    close_serial = False
    if serial is None:
        serial = get_serial(timeout)
        close_serial = True
        time.sleep(0.1)
    result = err = b""
    raw_on(serial)
    time.sleep(0.1)
    # Write the actual command and send CTRL-D to evaluate.
    for command in commands:
        command_bytes = command.encode("utf-8")
        for i in range(0, len(command_bytes), 32):
            serial.write(command_bytes[i : min(i + 32, len(command_bytes))])
            time.sleep(0.01)
        serial.write(b"\x04")
        response = serial.read_until(b"\x04>")  # Read until prompt.
        out, err = response[2:-2].split(b"\x04", 1)  # Split stdout, stderr
        result += out
        if err:
            return b"", err
    time.sleep(0.1)
    raw_off(serial)
    if close_serial:
        serial.close()
        time.sleep(0.1)
    return result, err


def clean_error(err: bytes) -> str:
    """
    Take stderr bytes returned from MicroPython and attempt to create a
    non-verbose error message.
    """
    if err:
        decoded = err.decode("utf-8")
        try:
            return decoded.split("\r\n")[-2]
        except Exception:
            return decoded
    return "There was an error."


def ls(serial: Serial | None = None, timeout: int = 10) -> list[str]:
    """
    List the files on the micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns a list of the files on the connected device or raises an IOError if
    there's a problem.
    """
    out, err = execute(
        [
            "import os",
            "print(os.listdir())",
        ],
        serial,
        timeout,
    )
    if err:
        raise IOError(clean_error(err))
    return ast.literal_eval(out.decode("utf-8"))


def rm(
    filename: str, serial: Serial | None = None, timeout: int = 10
) -> Literal[True]:
    """
    Removes a referenced file on the micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns True for success or raises an IOError if there's a problem.
    """
    commands = [
        "import os",
        "os.remove('{}')".format(filename),
    ]
    _out, err = execute(commands, serial, timeout)
    if err:
        raise IOError(clean_error(err))
    return True


def put(
    filename: str,
    target: str | None = None,
    serial: Serial | None = None,
    timeout: int = 10,
) -> Literal[True]:
    """
    Puts a referenced file on the LOCAL file system onto the
    file system on the BBC micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns True for success or raises an IOError if there's a problem.
    """
    if not os.path.isfile(filename):
        raise IOError("No such file.")
    with open(filename, "rb") as local:
        content = local.read()
    filename = os.path.basename(filename)
    if target is None:
        target = filename
    commands = [
        "fd = open('{}', 'wb')".format(target),
        "f = fd.write",
    ]
    while content:
        line = content[:64]
        commands.append("f(" + repr(line) + ")")
        content = content[64:]
    commands.append("fd.close()")
    _out, err = execute(commands, serial, timeout)
    if err:
        raise IOError(clean_error(err))
    return True


def get(
    filename: str,
    target: str | None = None,
    serial: Serial | None = None,
    timeout: int = 10,
) -> Literal[True]:
    """
    Gets a referenced file on the device's file system and copies it to the
    target (or current working directory if unspecified).

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns True for success or raises an IOError if there's a problem.
    """
    if target is None:
        target = filename
    commands = [
        "\n".join([
            "try:",
            " from microbit import uart as u",
            "except ImportError:",
            " try:",
            "  from machine import UART",
            "  u = UART(0, {})".format(SERIAL_BAUD_RATE),
            " except Exception:",
            "  try:",
            "   from sys import stdout as u",
            "  except Exception:",
            "   raise Exception('Could not find UART module in device.')",
        ]),
        "f = open('{}', 'rb')".format(filename),
        "r = f.read",
        "result = True",
        "\n".join([
            "while result:",
            " result = r(32)",
            " if result:",
            "  u.write(repr(result))",
        ]),
        "f.close()",
    ]
    out, err = execute(commands, serial, timeout)
    if err:
        raise IOError(clean_error(err))
    # Recombine the bytes while removing "b'" from start and "'" from end.
    assert out.startswith(b"b'") or out.startswith(b'b"')
    assert out.endswith(b"'") or out.endswith(b'"')
    out = eval(out)
    with open(target, "wb") as f:
        f.write(out)
    return True


def version(serial: Serial | None = None, timeout: int = 10) -> dict[str, str]:
    """
    Returns version information for MicroPython running on the connected
    device.

    If such information is not available or the device is not running
    MicroPython, raise a ValueError.

    If any other exception is thrown, the device was running MicroPython but
    there was a problem parsing the output.
    """
    try:
        out, err = execute(
            [
                "import os",
                "print(os.uname())",
            ],
            serial,
            timeout,
        )
        if err:
            raise ValueError(clean_error(err))
    except ValueError:
        # Re-raise any errors from stderr raised in the try block.
        raise
    except Exception:
        # Raise a value error to indicate unable to find something on the
        # microbit that will return parseable information about the version.
        # It doesn't matter what the error is, we just need to indicate a
        # failure with the expected ValueError exception.
        raise ValueError()
    raw = out.decode("utf-8").strip()
    raw = raw[1:-1]
    items = raw.split(", ")
    result: dict[str, str] = {}
    for item in items:
        key, value = item.split("=")
        result[key] = value[1:-1]
    return result


def main(argv: list[str] | None = None) -> None:
    """
    Entry point for the command line tool 'ufs'.

    Takes the args and processes them as per the documentation. :-)

    Exceptions are caught and printed for the user.
    """
    if not argv:
        argv = sys.argv[1:]
    try:
        global command_line_flag
        command_line_flag = True

        parser = argparse.ArgumentParser(description=_HELP_TEXT)

        subparsers = parser.add_subparsers(
            dest="command", help="One of 'ls', 'rm', 'put' or 'get'"
        )

        ls_parser = subparsers.add_parser("ls")
        ls_parser.add_argument(
            "delimiter",
            nargs="?",
            default=" ",
            help='Specify a delimiter string (default is whitespace). Eg. ";"',
        )
        ls_parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            help="How long we should wait for the device to respond (in seconds)",
            default=10,
        )

        rm_parser = subparsers.add_parser("rm")
        rm_parser.add_argument(
            "path", nargs="?", help="Specify a target filename."
        )
        rm_parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            help="How long we should wait for the device to respond (in seconds)",
            default=10,
        )

        get_parser = subparsers.add_parser("get")
        get_parser.add_argument(
            "path", nargs="?", help="Use when a file needs referencing."
        )
        get_parser.add_argument(
            "target", nargs="?", help="Specify a target filename."
        )
        get_parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            help="How long we should wait for the device to respond (in seconds)",
            default=10,
        )

        put_parser = subparsers.add_parser("put")
        put_parser.add_argument(
            "path", nargs="?", help="Use when a file needs referencing."
        )
        put_parser.add_argument(
            "target", nargs="?", help="Specify a target filename."
        )
        put_parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            help="How long we should wait for the device to respond (in seconds)",
            default=10,
        )

        args = parser.parse_args(argv)
        if args.command == "ls":
            list_of_files = ls(args.timeout)
            if list_of_files:
                print(args.delimiter.join(list_of_files))
        elif args.command == "rm":
            if args.path:
                rm(args.path, args.timeout)
            else:
                print('rm: missing filename. (e.g. "ufs rm foo.txt")')
                sys.exit(2)
        elif args.command == "put":
            if args.path:
                put(args.path, args.target, args.timeout)
            else:
                print('put: missing filename. (e.g. "ufs put foo.txt")')
                sys.exit(2)
        elif args.command == "get":
            if args.path:
                get(args.path, args.target, args.timeout)
            else:
                print('get: missing filename. (e.g. "ufs get foo.txt")')
                sys.exit(2)
        else:
            # Display some help.
            parser.print_help()
    except Exception as ex:
        # The exception of no return. Print exception information.
        print(ex)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
