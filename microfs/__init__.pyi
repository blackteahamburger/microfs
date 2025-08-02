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
import logging
import pathlib
from collections.abc import Callable as Callable
from typing import Final, Literal

from serial import Serial

SERIAL_BAUD_RATE: Final[int]
logger: logging.Logger

class MicroBitError(OSError): ...
class MicroBitIOError(MicroBitError): ...
class MicroBitNotFoundError(MicroBitError): ...

def find_microbit() -> tuple[str, str | None] | tuple[None, None]: ...
def flush_to_msg(serial: Serial, msg: bytes) -> None: ...
def flush(serial: Serial) -> None: ...
def raw_on(serial: Serial) -> None: ...
def raw_off(serial: Serial) -> None: ...
def get_serial(timeout: int = 10) -> Serial: ...
def clean_error(err: bytes) -> str: ...
def execute(
    commands: list[str], serial: Serial | None = None, timeout: int = 10
) -> bytes: ...
def ls(serial: Serial | None = None, timeout: int = 10) -> list[str]: ...
def rm(
    filename: str, serial: Serial | None = None, timeout: int = 10
) -> Literal[True]: ...
def put(
    filename: pathlib.Path,
    target: str | None = None,
    serial: Serial | None = None,
    timeout: int = 10,
) -> Literal[True]: ...
def get(
    filename: str,
    target: pathlib.Path | None = None,
    serial: Serial | None = None,
    timeout: int = 10,
) -> Literal[True]: ...
def version(
    serial: Serial | None = None, timeout: int = 10
) -> dict[str, str]: ...
def main(argv: list[str] | None = None) -> None: ...
