# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
# Copyright (c) 2016 Nicholas H.Tollervey
#
# See the LICENSE file for more information.
"""Entry point for the command line tool 'ufs'."""

import argparse
import importlib.metadata
import logging
import pathlib
import sys
from typing import TYPE_CHECKING

from serial import SerialException, SerialTimeoutException

from microfs.lib import (
    MicroBitIOError,
    MicroBitNotFoundError,
    MicroBitSerial,
    cat,
    cp,
    du,
    get,
    ls,
    micropython_version,
    mv,
    put,
    rm,
    version,
)

if TYPE_CHECKING:
    from collections.abc import Callable  # pragma: no cover


def _handle_ls(args: argparse.Namespace) -> None:
    list_of_files = ls(args.serial)
    if list_of_files:
        print(args.delimiter.join(list_of_files))  # noqa: T201


def _handle_cp(args: argparse.Namespace) -> None:
    cp(args.serial, args.src, args.dst)


def _handle_mv(args: argparse.Namespace) -> None:
    mv(args.serial, args.src, args.dst)


def _handle_rm(args: argparse.Namespace) -> None:
    rm(args.serial, args.paths)


def _handle_cat(args: argparse.Namespace) -> None:
    print(cat(args.serial, args.path))  # noqa: T201


def _handle_du(args: argparse.Namespace) -> None:
    print(du(args.serial, args.path))  # noqa: T201


def _handle_put(args: argparse.Namespace) -> None:
    put(args.serial, args.path, args.target)


def _handle_get(args: argparse.Namespace) -> None:
    get(args.serial, args.path, args.target)


def _handle_version(args: argparse.Namespace) -> None:
    if args.micropython:
        print(micropython_version(args.serial))  # noqa: T201
    else:
        version_info = version(args.serial)
        for key, value in version_info.items():
            print(f"{key}: {value}")  # noqa: T201


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ufs",
        description="Interact with the filesystem on a connected"
        "BBC micro:bit device.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"MicroFS version: {importlib.metadata.version('microfs2')}",
        help="output version information of microfs and exit",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        help="Device response timeout in seconds.\nDefaults to 10.",
        default=10,
    )
    parser.add_argument(
        "-s",
        "--serial",
        type=str,
        help="Specify the serial port of micro:bit (e.g. /dev/ttyACM0).",
        default=None,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", required=True
    )

    ls_parser = subparsers.add_parser(
        "ls",
        help="List files on the device.\nBased on the Unix command.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ls_parser.add_argument(
        "-d",
        "--delimiter",
        nargs="?",
        default=" ",
        help='Specify a delimiter string (e.g. ";")\nDefaults to whitespace)',
    )

    rm_parser = subparsers.add_parser(
        "rm",
        help="Remove a named file on the device.\nBased on the Unix command.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    rm_parser.add_argument(
        "paths", nargs="+", help="Specify one or more target filenames."
    )

    cp_parser = subparsers.add_parser(
        "cp",
        help="Copy a file from one location to another on the device.\n"
        "Based on the Unix command.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    cp_parser.add_argument("src", help="Source filename on micro:bit.")
    cp_parser.add_argument("dst", help="Destination filename on micro:bit.")

    mv_parser = subparsers.add_parser(
        "mv",
        help="Move a file from one location to another on the device.\n"
        "Based on the Unix command.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    mv_parser.add_argument("src", help="Source filename on micro:bit.")
    mv_parser.add_argument("dst", help="Destination filename on micro:bit.")

    cat_parser = subparsers.add_parser(
        "cat",
        help="Display the contents of a file on the device.\n"
        "Based on the Unix command.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    cat_parser.add_argument("path", help="The file to display.")

    du_parser = subparsers.add_parser(
        "du",
        help="Get the size of a file on the device in bytes.\n"
        "Based on the Unix command.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    du_parser.add_argument("path", help="The file to check du.")

    get_parser = subparsers.add_parser(
        "get",
        help="Copy a named file from the device to the local file system.\n"
        "FTP equivalent.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    get_parser.add_argument(
        "path", help="The name of the file to copy from the micro:bit."
    )
    get_parser.add_argument(
        "target",
        type=pathlib.Path,
        nargs="?",
        help="The local path to copy the micro:bit file to.\n"
        "Defaults to the name of the file on the micro:bit.",
    )

    put_parser = subparsers.add_parser(
        "put",
        help="Copy a named local file onto the device.\nFTP equivalent.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    put_parser.add_argument(
        "path",
        type=pathlib.Path,
        help="The local file to copy onto the micro:bit.",
    )
    put_parser.add_argument(
        "target",
        nargs="?",
        help="The name of the file on the micro:bit.\n"
        "Defaults to the name of the local file.",
    )

    version_parser = subparsers.add_parser(
        "version",
        help="Return information identifying "
        "the current operating system on the device.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    version_parser.add_argument(
        "-m",
        "--micropython",
        action="store_true",
        help="Show MicroPython version information only.",
    )
    return parser


def _run_command(args: argparse.Namespace) -> None:
    if args.serial is not None:
        args.serial = MicroBitSerial(args.serial, timeout=args.timeout)
    else:
        args.serial = MicroBitSerial.get_serial()
    with args.serial:
        _dispatch_command(args)


def _dispatch_command(args: argparse.Namespace) -> None:
    handlers: dict[str, Callable[..., None]] = {
        "ls": _handle_ls,
        "rm": _handle_rm,
        "cp": _handle_cp,
        "mv": _handle_mv,
        "cat": _handle_cat,
        "du": _handle_du,
        "put": _handle_put,
        "get": _handle_get,
        "version": _handle_version,
    }
    if args.command in handlers:
        handlers[args.command](args)


def main() -> None:
    """Entry point for the command line tool 'ufs'."""
    argv = sys.argv[1:]
    logger: logging.Logger = logging.getLogger(__name__)
    logging.basicConfig(format="%(levelname)s:%(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        _run_command(args)
    except MicroBitIOError as e:
        logger.error(  # noqa: TRY400
            "An I/O error occurred with the BBC micro:bit device: %s", e
        )
        sys.exit(1)
    except MicroBitNotFoundError as e:
        logger.error("The BBC micro:bit device is not connected: %s", e)  # noqa: TRY400
        sys.exit(1)
    except SerialTimeoutException as e:
        logger.error("Serial communication timed out: %s", e)  # noqa: TRY400
        sys.exit(1)
    except SerialException as e:
        logger.error("Serial communication error: %s", e)  # noqa: TRY400
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)  # noqa: TRY400
        sys.exit(1)
    except IsADirectoryError as e:
        logger.error("Expected a file but found a directory: %s", e)  # noqa: TRY400
        sys.exit(1)
    except Exception:
        logger.exception("An unknown error occurred during execution.")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
