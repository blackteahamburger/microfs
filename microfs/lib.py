# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
# Copyright (c) 2016 Nicholas H.Tollervey
#
# See the LICENSE file for more information.
"""Functions for file system operations on the BBC micro:bit."""

from __future__ import annotations

import ast
import contextlib
import pathlib
import time
from typing import TYPE_CHECKING, Final, Self

from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE, Serial
from serial.tools.list_ports import comports as list_serial_ports

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    from _typeshed import ReadableBuffer
    from serial.tools.list_ports_linux import SysFS


class MicroBitError(OSError):
    """Base class for exceptions related to the BBC micro:bit."""


class MicroBitIOError(MicroBitError):
    """Exception raised for I/O errors related to the BBC micro:bit."""


class MicroBitNotFoundError(MicroBitError):
    """Exception raised when the BBC micro:bit is not found."""


class MicroBitSerial(Serial):
    """Serial class for micro:bit with micro:bit specific helpers."""

    SERIAL_BAUD_RATE: Final = 115200
    DEFAULT_TIMEOUT: Final = 10

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        port: str | None = None,
        baudrate: int = SERIAL_BAUD_RATE,
        bytesize: int = EIGHTBITS,
        parity: str = PARITY_NONE,
        stopbits: int = STOPBITS_ONE,
        timeout: int = DEFAULT_TIMEOUT,
        xonxoff: bool = False,
        rtscts: bool = False,
        write_timeout: float | None = None,
        dsrdtr: bool = False,
        inter_byte_timeout: float | None = None,
        exclusive: bool | None = None,
        **kwargs: float,
    ) -> None:
        """
        Initialize comm port object with micro:bit specific defaults.

        Args:
            port: The serial port to connect to.
            baudrate: The baud rate for the serial connection.
            bytesize: The number of data bits.
            parity: The parity setting for the serial connection.
            stopbits: The number of stop bits.
            timeout: The read timeout for the serial connection.
            xonxoff: Enable software flow control.
            rtscts: Enable hardware (RTS/CTS) flow control.
            write_timeout: The write timeout for the serial connection.
            dsrdtr: Enable hardware (DSR/DTR) flow control.
            inter_byte_timeout: The timeout between bytes.
            exclusive: Whether to open the port in exclusive mode.
            kwargs: Additional keyword arguments.

        """
        super().__init__(
            port,
            baudrate,
            bytesize,
            parity,
            stopbits,
            timeout,
            xonxoff,
            rtscts,
            write_timeout,
            dsrdtr,
            inter_byte_timeout,
            exclusive,
            **kwargs,
        )

    @staticmethod
    def find_microbit() -> SysFS | None:
        """
        Find a connected the BBC micro:bit device.

        Returns:
            The port for a connected micro:bit device.
            If no device is connected the result will be None.

        """
        ports = list_serial_ports()
        for port in ports:
            if "VID:PID=0D28:0204" in port[2].upper():
                return port
        return None

    @classmethod
    def get_serial(cls, timeout: int = 10) -> Self:
        """
        Return a MicroBitSerial object for a connected micro:bit.

        Args:
            timeout: Device response timeout.

        Raises:
            MicroBitNotFoundError: If no micro:bit is found.

        Returns:
            A MicroBitSerial object.

        """
        port = cls.find_microbit()
        if port is None:
            msg = "Could not find micro:bit."
            raise MicroBitNotFoundError(msg)
        return cls(port[0], timeout=timeout)

    def __enter__(self) -> Self:
        """
        Enter context: open port if needed and enter raw mode.

        Returns:
            The MicroBitSerial object.

        """
        super().__enter__()
        self.raw_on()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exit context: leave raw mode and close port.

        Args:
            exc_type: The type of the exception raised, if any.
            exc_val: The value of the exception raised, if any.
            exc_tb: The traceback of the exception raised, if any.

        """
        with contextlib.suppress(Exception):
            self.raw_off()
        super().__exit__(exc_type, exc_val, exc_tb)

    def close(self) -> None:
        """Close port and sleep to avoid data floods."""
        super().close()
        time.sleep(0.1)

    def write(self, b: ReadableBuffer) -> int | None:
        """
        Write bytes to the serial port and sleep briefly.

        Args:
            b: The byte string to write.

        Returns:
            The number of bytes written, or None if the port is not open.

        """
        result = super().write(b)
        time.sleep(0.01)
        return result

    def flush_to_msg(self, msg: bytes) -> None:
        """
        Read the rx serial data until we reach an expected message.

        Args:
            msg: The expected message to read until.

        Raises:
            MicroBitIOError: If raw REPL could not be entered.

        """
        data = self.read_until(msg)
        if not data.endswith(msg):
            err = "Error: Could not enter raw REPL, "
            f"expected: {msg}, got: {data}"
            raise MicroBitIOError(err)

    def flush(self) -> None:
        """Flush all rx input without relying on serial.flushInput()."""
        n = self.in_waiting
        while n > 0:
            self.read(n)
            n = self.in_waiting

    def raw_on(self) -> None:
        """Put the device into raw mode."""
        raw_repl_msg = b"raw REPL; CTRL-B to exit\r\n>"
        # Send CTRL-B to end raw mode if required.
        self.write(b"\x02")
        # Send CTRL-C three times between pauses to break out of loop.
        for _ in range(3):
            self.write(b"\r\x03")
        self.flush()
        # Go into raw mode with CTRL-A.
        self.write(b"\r\x01")
        self.flush_to_msg(raw_repl_msg)
        # Soft Reset with CTRL-D
        self.write(b"\x04")
        self.flush_to_msg(b"soft reboot\r\n")
        # Some MicroPython versions/ports/forks provide a different message
        # after a Soft Reset, check if we are in raw REPL
        # if not send a CTRL-A again
        data = self.read_until(raw_repl_msg)
        if not data.endswith(raw_repl_msg):
            self.write(b"\r\x01")
            self.flush_to_msg(raw_repl_msg)
        self.flush()
        time.sleep(0.1)

    def raw_off(self) -> None:
        """Take the device out of raw mode."""
        self.write(b"\x02")  # Send CTRL-B to get out of raw mode.
        time.sleep(0.1)

    def write_command(self, command: str) -> bytes:
        """
        Send a command to the micro:bit and return the result.

        Args:
            command: The command to send to the micro:bit.

        Raises:
            MicroBitIOError: If there's a problem with the commands sent.

        Returns:
            The stdout output from the micro:bit.

        """
        command_bytes = command.encode()
        for i in range(0, len(command_bytes), 32):
            self.write(command_bytes[i : min(i + 32, len(command_bytes))])
        self.write(b"\x04")
        response = self.read_until(b"\x04>")  # Read until prompt.
        out, err = response[2:-2].split(b"\x04", 1)  # Split stdout, stderr
        if err:
            decoded = err.decode()
            try:
                msg = decoded.split("\r\n")[-2]
            except IndexError:
                msg = decoded
            raise MicroBitIOError(msg or "There was an error.")
        return out

    def write_commands(self, commands: Iterable[str]) -> bytes:
        """
        Send multiple commands to the micro:bit and return the result.

        For this to work correctly, a particular sequence of commands needs to
        be sent to put the device into a good state to process the incoming
        command.

        Args:
            commands: An iterable of commands to send to the micro:bit.

        Returns:
            The stdout output from the micro:bit.

        """
        result = b""
        for command in commands:
            result += self.write_command(command)
        return result


def ls(serial: MicroBitSerial) -> list[str]:
    """
    List the files on the micro:bit.

    Args:
        serial: The serial connection to the device.

    Returns:
        A list of the files on the connected device.

    """
    out = serial.write_commands(["import os", "print(os.listdir())"])
    return ast.literal_eval(out.decode())


def cp(serial: MicroBitSerial, src: str, dst: str) -> None:
    """
    Copy a file on the micro:bit filesystem.

    Args:
        serial: Serial connection.
        src: Source filename on micro:bit.
        dst: Destination filename on micro:bit.

    """
    commands = [
        f"with open('{src}', 'rb') as fsrc, open('{dst}', 'wb') as fdst: "
        "fdst.write(fsrc.read())"
    ]
    serial.write_commands(commands)


def mv(serial: MicroBitSerial, src: str, dst: str) -> None:
    """
    Move a file on the micro:bit filesystem.

    Args:
        serial: Serial connection.
        src: Source filename on micro:bit.
        dst: Destination filename on micro:bit.

    """
    cp(serial, src, dst)
    rm(serial, [src])


def rm(serial: MicroBitSerial, filenames: Iterable[str]) -> None:
    """
    Remove referenced files on the micro:bit.

    Args:
        serial: Serial connection.
        filenames: A list of file names to remove.

    """
    commands = ["import os"]
    commands.extend(f"os.remove('{filename}')" for filename in filenames)
    serial.write_commands(commands)


def cat(serial: MicroBitSerial, filename: str) -> str:
    """
    Print the contents of a file on the micro:bit.

    Args:
        serial: Serial connection.
        filename: The file to display.

    Returns:
        The file content as string.

    """
    commands = [f"with open('{filename}', 'r') as f: print(f.read())"]
    out = serial.write_commands(commands)
    return out.decode()


def du(serial: MicroBitSerial, filename: str) -> int:
    """
    Get the size of a file on the micro:bit in bytes.

    Args:
        serial: Serial connection.
        filename: The file to check.

    Returns:
        Size in bytes.

    """
    commands = ["import os", f"print(os.size('{filename}'))"]
    out = serial.write_commands(commands)
    return int(out.decode().strip())


def put(
    serial: MicroBitSerial, filename: pathlib.Path, target: str | None = None
) -> None:
    """
    Copy a local file onto the BBC micro:bit file system.

    Args:
        serial: The serial connection to the device.
        filename: The local file to copy onto the micro:bit.
        target: The name of the file on the micro:bit (defaults to the name of
        the local file).

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
    serial.write_commands(commands)


def get(
    serial: MicroBitSerial, filename: str, target: pathlib.Path | None = None
) -> None:
    """
    Get a referenced file on the BBC micro:bit file system.

    Copies the file to the target or current working directory if unspecified.

    Args:
        serial: The serial connection to the device.
        filename: The name of the file to copy from the micro:bit.
        target: The local file to copy the micro:bit file to (defaults to the
        name of the file on the micro:bit).

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
            f"  u = UART(0, {MicroBitSerial.SERIAL_BAUD_RATE})",
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
    out = serial.write_commands(commands)
    # Recombine the bytes while removing "b'" from start and "'" from end.
    if not out.startswith((b"b'", b'b"')) or not out.endswith((b"'", b'"')):
        msg = "Unexpected file data format received from device."
        raise MicroBitIOError(msg)
    out = ast.literal_eval(out.decode())
    with target.open("wb") as f:
        f.write(out)


def version(serial: MicroBitSerial) -> dict[str, str]:
    """
    Return version information for MicroPython running on the connected device.

    Args:
        serial: The serial connection to the device.

    Returns:
        A dictionary containing version information.

    """
    out = serial.write_commands(["import os", "print(os.uname())"])
    raw = out.decode().strip()
    raw = raw[1:-1]
    items = raw.split(", ")
    result: dict[str, str] = {}
    for item in items:
        key, value = item.split("=")
        result[key] = value[1:-1]
    return result
