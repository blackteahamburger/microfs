# Copyright (c) 2026 Blackteahamburger <blackteahamburger@outlook.com>
#
# See the LICENSE file for more information.
"""Exceptions for operations on the BBC micro:bit."""


class MicroBitError(RuntimeError):
    """Base class for exceptions related to the BBC micro:bit."""


class MicroBitNotFoundError(MicroBitError):
    """Exception raised when the BBC micro:bit is not found."""


class MicroBitIOError(MicroBitError, OSError):
    """Exception raised for I/O errors related to the BBC micro:bit."""


class MicroBitBaseException(MicroBitError, BaseException):
    """Exception raised for BaseException on the BBC micro:bit."""


class MicroBitArithmeticError(MicroBitError, ArithmeticError):
    """Exception raised for ArithmeticError on the BBC micro:bit."""


class MicroBitAssertionError(MicroBitError, AssertionError):
    """Exception raised for AssertionError on the BBC micro:bit."""


class MicroBitAttributeError(MicroBitError, AttributeError):
    """Exception raised for AttributeError on the BBC micro:bit."""


class MicroBitEOFError(MicroBitError, EOFError):
    """Exception raised for EOFError on the BBC micro:bit."""


class MicroBitException(MicroBitError, Exception):
    """Exception raised for Exception on the BBC micro:bit."""


class MicroBitGeneratorExit(MicroBitError, GeneratorExit):
    """Exception raised for GeneratorExit on the BBC micro:bit."""


class MicroBitImportError(MicroBitError, ImportError):
    """Exception raised for ImportError on the BBC micro:bit."""


class MicroBitIndentationError(MicroBitError, IndentationError):
    """Exception raised for IndentationError on the BBC micro:bit."""


class MicroBitIndexError(MicroBitError, IndexError):
    """Exception raised for IndexError on the BBC micro:bit."""


class MicroBitKeyboardInterrupt(MicroBitError, KeyboardInterrupt):
    """Exception raised for KeyboardInterrupt on the BBC micro:bit."""


class MicroBitKeyError(MicroBitError, KeyError):
    """Exception raised for KeyError on the BBC micro:bit."""


class MicroBitLookupError(MicroBitError, LookupError):
    """Exception raised for LookupError on the BBC micro:bit."""


class MicroBitMemoryError(MicroBitError, MemoryError):
    """Exception raised for MemoryError on the BBC micro:bit."""


class MicroBitNameError(MicroBitError, NameError):
    """Exception raised for NameError on the BBC micro:bit."""


class MicroBitNotImplementedError(MicroBitError, NotImplementedError):
    """Exception raised for NotImplementedError on the BBC micro:bit."""


class MicroBitOSError(MicroBitError, OSError):
    """Exception raised for OSError on the BBC micro:bit."""


class MicroBitOverflowError(MicroBitError, OverflowError):
    """Exception raised for OverflowError on the BBC micro:bit."""


class MicroBitRuntimeError(MicroBitError, RuntimeError):
    """Exception raised for RuntimeError on the BBC micro:bit."""


class MicroBitStopAsyncIteration(MicroBitError, StopAsyncIteration):
    """Exception raised for StopAsyncIteration on the BBC micro:bit."""


class MicroBitStopIteration(MicroBitError, StopIteration):
    """Exception raised for StopIteration on the BBC micro:bit."""


class MicroBitSyntaxError(MicroBitError, SyntaxError):
    """Exception raised for SyntaxError on the BBC micro:bit."""


class MicroBitSystemExit(MicroBitError, SystemExit):
    """Exception raised for SystemExit on the BBC micro:bit."""


class MicroBitTypeError(MicroBitError, TypeError):
    """Exception raised for TypeError on the BBC micro:bit."""


class MicroBitUnicodeError(MicroBitError, UnicodeError):
    """Exception raised for UnicodeError on the BBC micro:bit."""


class MicroBitValueError(MicroBitError, ValueError):
    """Exception raised for ValueError on the BBC micro:bit."""


class MicroBitZeroDivisionError(MicroBitError, ZeroDivisionError):
    """Exception raised for ZeroDivisionError on the BBC micro:bit."""
