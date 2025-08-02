# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Functions for basic file system operations on the BBC micro:bit.

The following commands are available:

* ls - list files on the device. Based on the equivalent Unix command.
* rm - remove a named file on the device. Based on the Unix command.
* put - copy a named local file onto the device a la equivalent FTP command.
* get - copy a named file from the device to the local file system a la FTP.
* version - get version information for MicroPython running on the device.
"""

import argparse
import ast
import importlib.metadata
import logging
import pathlib
import sys
import time
from typing import TYPE_CHECKING, Final, Literal

from serial import Serial
from serial.tools.list_ports import comports as list_serial_ports

if TYPE_CHECKING:
    from collections.abc import Callable  # pragma: no cover

#: The help text to be shown when requested.
_HELP_TEXT: Final = """
Interact with the basic filesystem on a connected the BBC micro:bit device.

The following commands are available:

* ls - list files on the device. Based on the equivalent Unix command.
* rm - remove a named file on the device. Based on the Unix command.
* put - copy a named local file onto the device a la equivalent FTP command.
* get - copy a named file from the device to the local file system a la FTP.
* version - get version information for MicroPython running on the device.
"""

SERIAL_BAUD_RATE: Final = 115200

logger: logging.Logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MicroBitError(OSError):
    """Base class for exceptions related to the BBC micro:bit."""


class MicroBitIOError(MicroBitError):
    """Exception raised for I/O errors related to the BBC micro:bit."""


class MicroBitNotFoundError(MicroBitError):
    """Exception raised when the BBC micro:bit is not found."""


def find_microbit() -> tuple[str, str | None] | tuple[None, None]:
    """
    Find a connected the BBC micro:bit device.

    Returns:
        a tuple representation of the port and serial number for a
        connected micro:bit device. If no device is connected the tuple will be
        (None, None).

    """
    ports = list_serial_ports()
    for port in ports:
        if "VID:PID=0D28:0204" in port[2].upper():
            return (port[0], port.serial_number)
    return (None, None)


def flush_to_msg(serial: Serial, msg: bytes) -> None:
    """
    Read the rx serial data until we reach an expected message.

    Args:
        serial: The serial connection to the device.
        msg: The expected message to read until.

    Raises:
        MicroBitIOError: If raw REPL could not be entered.

    """
    data = serial.read_until(msg)
    if not data.endswith(msg):
        err = f"Error: Could not enter raw REPL, expected: {msg}, got: {data}"
        raise MicroBitIOError(err)


def flush(serial: Serial) -> None:
    """
    Flush all rx input without relying on serial.flushInput().

    Args:
        serial: The serial connection to the device.

    """
    n = serial.in_waiting
    while n > 0:
        serial.read(n)
        n = serial.in_waiting


def raw_on(serial: Serial) -> None:
    """
    Put the device into raw mode.

    Args:
        serial: The serial connection to the device.

    """
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
    Take the device out of raw mode.

    Args:
        serial: The serial connection to the device.

    """
    serial.write(b"\x02")  # Send CTRL-B to get out of raw mode.


def get_serial(timeout: int = 10) -> Serial:
    """
    Detect if a micro:bit is connected and return a serial object to it.

    Args:
        timeout: The time in seconds to wait for the device to respond.

    Raises:
        MicroBitNotFoundError: If no micro:bit is found.

    Returns:
        A Serial object connected to the micro:bit.

    """
    port, _serial_number = find_microbit()
    if port is None:
        msg = "Could not find micro:bit."
        raise MicroBitNotFoundError(msg)
    return Serial(port, SERIAL_BAUD_RATE, timeout=timeout, parity="N")


def clean_error(err: bytes) -> str:
    """
    Convert MicroPython stderr bytes to a concise error message.

    Args:
        err: The stderr bytes returned from MicroPython.

    Returns:
        A cleaned up error message string.

    """
    if err:
        decoded = err.decode("utf-8")
        try:
            return decoded.split("\r\n")[-2]
        except IndexError:
            return decoded
    return "There was an error."


def execute(
    commands: list[str], serial: Serial | None = None, timeout: int = 10
) -> bytes:
    """
    Send commands to the connected micro:bit via serial and returns the result.

    If no serial connection is provided, attempts to autodetect the
    device.

    For this to work correctly, a particular sequence of commands needs to be
    sent to put the device into a good state to process the incoming command.

    Args:
        commands: A list of commands to send to the micro:bit.
        serial: An optional Serial object to use for communication.
        timeout: The time in seconds to wait for the device to respond.

    Raises:
        MicroBitIOError: If there's a problem with the commands sent.

    Returns:
        The stdout output from the micro:bit.

    """
    close_serial = False
    if serial is None:
        serial = get_serial(timeout)
        close_serial = True
        time.sleep(0.1)
    result = b""
    raw_on(serial)
    time.sleep(0.1)
    # Write the actual command and send CTRL-D to evaluate.
    for command in commands:
        command_bytes = command.encode()
        for i in range(0, len(command_bytes), 32):
            serial.write(command_bytes[i : min(i + 32, len(command_bytes))])
            time.sleep(0.01)
        serial.write(b"\x04")
        response = serial.read_until(b"\x04>")  # Read until prompt.
        out, err = response[2:-2].split(b"\x04", 1)  # Split stdout, stderr
        result += out
        if err:
            raise MicroBitIOError(clean_error(err))
    time.sleep(0.1)
    raw_off(serial)
    if close_serial:
        serial.close()
        time.sleep(0.1)
    return result


def ls(serial: Serial | None = None, timeout: int = 10) -> list[str]:
    """
    List the files on the micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Args:
        serial: The serial connection to the device.
        timeout: The time in seconds to wait for the device to respond.

    Returns:
        A list of the files on the connected device.

    """
    out = execute(["import os", "print(os.listdir())"], serial, timeout)
    return ast.literal_eval(out.decode())


def rm(
    filename: str, serial: Serial | None = None, timeout: int = 10
) -> Literal[True]:
    """
    Remove a referenced file on the micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Args:
        filename: The name of the file to remove.
        serial: The serial connection to the device.
        timeout: The time in seconds to wait for the device to respond.

    Returns:
        True for success.

    """
    commands = ["import os", f"os.remove('{filename}')"]
    execute(commands, serial, timeout)
    return True


def put(
    filename: pathlib.Path,
    target: str | None = None,
    serial: Serial | None = None,
    timeout: int = 10,
) -> Literal[True]:
    """
    Copy a local file onto the BBC micro:bit file system.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Args:
        filename: The local file to copy onto the micro:bit.
        target: The name of the file on the micro:bit (defaults to the name of
        the local file).
        serial: The serial connection to the device.
        timeout: The time in seconds to wait for the device to respond.

    Raises:
        FileNotFoundError: If the specified file does not exist.

    Returns:
        True for success.

    """
    if not filename.is_file():
        msg = "No such file."
        raise FileNotFoundError(msg)
    with filename.open("rb") as local:
        content = local.read()
    if target is None:
        target = filename.name
    commands = [f"fd = open('{target}', 'wb')", "f = fd.write"]
    while content:
        line = content[:64]
        commands.append("f(" + repr(line) + ")")
        content = content[64:]
    commands.append("fd.close()")
    execute(commands, serial, timeout)
    return True


def get(
    filename: str,
    target: pathlib.Path | None = None,
    serial: Serial | None = None,
    timeout: int = 10,
) -> Literal[True]:
    """
    Get a referenced file on the BBC micro:bit file system.

    Copies the file to the target or current working directory if unspecified.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Args:
        filename: The name of the file to copy from the micro:bit.
        target: The local file to copy the micro:bit file to (defaults to the
        name of the file on the micro:bit).
        serial: The serial connection to the device.
        timeout: The time in seconds to wait for the device to respond.

    Raises:
        MicroBitIOError: If file data format received from device is invalid.

    Returns:
        True for success.

    """
    if target is None:
        target = pathlib.Path(filename)
    commands = [
        "\n".join([
            "try:",
            " from microbit import uart as u",
            "except ImportError:",
            " try:",
            "  from machine import UART",
            f"  u = UART(0, {SERIAL_BAUD_RATE})",
            " except Exception:",
            "  try:",
            "   from sys import stdout as u",
            "  except Exception:",
            "   raise Exception('Could not find UART module in device.')",
        ]),
        f"f = open('{filename}', 'rb')",
        "r = f.read",
        "result = True",
        "while result:\n result = r(32)\n if result:\n  u.write(repr(result))",
        "f.close()",
    ]
    out = execute(commands, serial, timeout)
    # Recombine the bytes while removing "b'" from start and "'" from end.
    if not out.startswith((b"b'", b'b"')) or not out.endswith((b"'", b'"')):
        msg = "Unexpected file data format received from device."
        raise MicroBitIOError(msg)
    out = ast.literal_eval(out.decode())
    with target.open("wb") as f:
        f.write(out)
    return True


def version(serial: Serial | None = None, timeout: int = 10) -> dict[str, str]:
    """
    Return version information for MicroPython running on the connected device.

    Args:
        serial: The serial connection to the device.
        timeout: The time in seconds to wait for the device to respond.

    Returns:
        A dictionary containing version information.

    """
    out = execute(["import os", "print(os.uname())"], serial, timeout)
    raw = out.decode("utf-8").strip()
    raw = raw[1:-1]
    items = raw.split(", ")
    result: dict[str, str] = {}
    for item in items:
        key, value = item.split("=")
        result[key] = value[1:-1]
    return result


def _handle_ls(args: argparse.Namespace) -> None:
    list_of_files = ls(timeout=args.timeout)
    if list_of_files:
        logger.info("Found files: %s", args.delimiter.join(list_of_files))


def _handle_rm(args: argparse.Namespace) -> None:
    if args.path:
        rm(filename=args.path, timeout=args.timeout)
    else:
        logger.error('rm: error: missing filename. (e.g. "ufs rm foo.txt")')
        sys.exit(2)


def _handle_put(args: argparse.Namespace) -> None:
    if args.path:
        put(filename=args.path, target=args.target, timeout=args.timeout)
    else:
        logger.error('put: error: missing filename. (e.g. "ufs put foo.txt")')
        sys.exit(2)


def _handle_get(args: argparse.Namespace) -> None:
    if args.path:
        get(filename=args.path, target=args.target, timeout=args.timeout)
    else:
        logger.error('get: error: missing filename. (e.g. "ufs get foo.txt")')
        sys.exit(2)


def _handle_version(args: argparse.Namespace) -> None:
    version_info = version(timeout=args.timeout)
    for key, value in version_info.items():
        logger.info("%s: %s", key, value)


def main(argv: list[str] | None = None) -> None:
    """
    Entry point for the command line tool 'ufs'.

    Takes the args and processes them as per the documentation. :-)

    Exceptions are caught and printed for the user.

    Args:
        argv: The command line arguments to process. Uses sys.argv[1:] if None.

    """
    if argv is None:
        argv = sys.argv[1:]
    try:
        logger_handler = logging.StreamHandler()
        logger_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(logger_handler)
        logger.setLevel(logging.INFO)

        parser = argparse.ArgumentParser(
            description=_HELP_TEXT,
            formatter_class=argparse.RawTextHelpFormatter,
        )

        parser.add_argument(
            "--version",
            action="version",
            version="microfs version: "
            f"{importlib.metadata.version('microfs')}",
            help="output version information of microfs and exit",
        )

        subparsers = parser.add_subparsers(
            dest="command", help="One of 'ls', 'rm', 'put', 'get' or 'version'"
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
            help="How long we should wait for the device to respond "
            "(in seconds)",
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
            help="How long we should wait for the device to respond "
            "(in seconds)",
            default=10,
        )

        get_parser = subparsers.add_parser("get")
        get_parser.add_argument(
            "path", nargs="?", help="Use when a file needs referencing."
        )
        get_parser.add_argument(
            "target",
            type=pathlib.Path,
            nargs="?",
            help="Specify a target filename.",
        )
        get_parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            help="How long we should wait for the device to respond "
            "(in seconds)",
            default=10,
        )

        put_parser = subparsers.add_parser("put")
        put_parser.add_argument(
            "path",
            type=pathlib.Path,
            nargs="?",
            help="Use when a file needs referencing.",
        )
        put_parser.add_argument(
            "target", nargs="?", help="Specify a target filename."
        )
        put_parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            help="How long we should wait for the device to respond "
            "(in seconds)",
            default=10,
        )

        version_parser = subparsers.add_parser("version")
        version_parser.add_argument(
            "-t",
            "--timeout",
            type=int,
            help="How long we should wait for the device to respond "
            "(in seconds)",
            default=10,
        )

        args = parser.parse_args(argv)
        handlers: dict[str, Callable[..., None]] = {
            "ls": _handle_ls,
            "rm": _handle_rm,
            "put": _handle_put,
            "get": _handle_get,
            "version": _handle_version,
        }
        if args.command in handlers:
            handlers[args.command](args)
        else:
            # Display some help.
            parser.print_help()
    except Exception:
        # The exception of no return. Log exception information.
        logger.exception("An error occurred during execution:")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
