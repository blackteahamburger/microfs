# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
# Copyright (c) 2016 Nicholas H.Tollervey
#
# See the LICENSE file for more information.
"""Functions for file system operations on the BBC micro:bit."""

import ast
import pathlib
import time
from typing import Final

from serial import Serial
from serial.tools.list_ports import comports as list_serial_ports

SERIAL_BAUD_RATE: Final = 115200


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
        timeout: Device response timeout.

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
        decoded = err.decode()
        try:
            return decoded.split("\r\n")[-2]
        except IndexError:
            return decoded
    return "There was an error."


def execute(
    commands: list[str], timeout: int = 10, serial: Serial | None = None
) -> bytes:
    """
    Send commands to the connected micro:bit via serial and returns the result.

    If no serial connection is provided, attempts to autodetect the
    device.

    For this to work correctly, a particular sequence of commands needs to be
    sent to put the device into a good state to process the incoming command.

    Args:
        commands: A list of commands to send to the micro:bit.
        timeout: Device response timeout.
        serial: An optional Serial object to use for communication.

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


def ls(timeout: int = 10, serial: Serial | None = None) -> list[str]:
    """
    List the files on the micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Args:
        timeout: Device response timeout.
        serial: The serial connection to the device.

    Returns:
        A list of the files on the connected device.

    """
    out = execute(["import os", "print(os.listdir())"], timeout, serial)
    return ast.literal_eval(out.decode())


def cp(
    src: str, dst: str, timeout: int = 10, serial: Serial | None = None
) -> None:
    """
    Copy a file on the micro:bit filesystem.

    Args:
        src: Source filename on micro:bit.
        dst: Destination filename on micro:bit.
        timeout: Device response timeout.
        serial: Serial connection.

    """
    commands = [
        f"with open('{src}', 'rb') as fsrc, open('{dst}', 'wb') as fdst: "
        "fdst.write(fsrc.read())"
    ]
    execute(commands, timeout, serial)


def mv(
    src: str, dst: str, timeout: int = 10, serial: Serial | None = None
) -> None:
    """
    Move a file on the micro:bit filesystem.

    Args:
        src: Source filename on micro:bit.
        dst: Destination filename on micro:bit.
        timeout: Device response timeout.
        serial: Serial connection.

    """
    cp(src, dst, timeout, serial)
    rm([src], timeout, serial)


def rm(
    filenames: list[str], timeout: int = 10, serial: Serial | None = None
) -> None:
    """
    Remove referenced files on the micro:bit.

    Args:
        filenames: A list of file names to remove.
        timeout: Device response timeout.
        serial: The serial connection to the device.

    """
    commands = ["import os"]
    commands.extend(f"os.remove('{filename}')" for filename in filenames)
    execute(commands, timeout, serial)


def cat(filename: str, timeout: int = 10, serial: Serial | None = None) -> str:
    """
    Print the contents of a file on the micro:bit.

    Args:
        filename: The file to display.
        timeout: Device response timeout.
        serial: Serial connection.

    Returns:
        The file content as string.

    """
    commands = [f"with open('{filename}', 'r') as f: print(f.read())"]
    out = execute(commands, timeout, serial)
    return out.decode()


def du(filename: str, timeout: int = 10, serial: Serial | None = None) -> int:
    """
    Get the size of a file on the micro:bit in bytes.

    Args:
        filename: The file to check.
        timeout: Device response timeout.
        serial: Serial connection.

    Returns:
        Size in bytes.

    """
    commands = ["import os", f"print(os.size('{filename}'))"]
    out = execute(commands, timeout, serial)
    return int(out.decode().strip())


def put(
    filename: pathlib.Path,
    target: str | None = None,
    timeout: int = 10,
    serial: Serial | None = None,
) -> None:
    """
    Copy a local file onto the BBC micro:bit file system.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Args:
        filename: The local file to copy onto the micro:bit.
        target: The name of the file on the micro:bit (defaults to the name of
        the local file).
        timeout: Device response timeout.
        serial: The serial connection to the device.

    """
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
    execute(commands, timeout, serial)


def get(
    filename: str,
    target: pathlib.Path | None = None,
    timeout: int = 10,
    serial: Serial | None = None,
) -> None:
    """
    Get a referenced file on the BBC micro:bit file system.

    Copies the file to the target or current working directory if unspecified.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Args:
        filename: The name of the file to copy from the micro:bit.
        target: The local file to copy the micro:bit file to (defaults to the
        name of the file on the micro:bit).
        force: Whether to overwrite the target file if it already exists.
        timeout: Device response timeout.
        serial: The serial connection to the device.

    Raises:
        MicroBitIOError: If file data format received from device is invalid.

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
    out = execute(commands, timeout, serial)
    # Recombine the bytes while removing "b'" from start and "'" from end.
    if not out.startswith((b"b'", b'b"')) or not out.endswith((b"'", b'"')):
        msg = "Unexpected file data format received from device."
        raise MicroBitIOError(msg)
    out = ast.literal_eval(out.decode())
    with target.open("wb") as f:
        f.write(out)


def version(timeout: int = 10, serial: Serial | None = None) -> dict[str, str]:
    """
    Return version information for MicroPython running on the connected device.

    Args:
        timeout: Device response timeout.
        serial: The serial connection to the device.

    Returns:
        A dictionary containing version information.

    """
    out = execute(["import os", "print(os.uname())"], timeout, serial)
    raw = out.decode().strip()
    raw = raw[1:-1]
    items = raw.split(", ")
    result: dict[str, str] = {}
    for item in items:
        key, value = item.split("=")
        result[key] = value[1:-1]
    return result
