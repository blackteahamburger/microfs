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

from microfs.lib import (
    MicroBitIOError,
    MicroBitNotFoundError,
    cat,
    cp,
    du,
    get,
    ls,
    mv,
    put,
    rm,
    version,
)

if TYPE_CHECKING:
    from collections.abc import Callable  # pragma: no cover


def _handle_ls(args: argparse.Namespace) -> None:
    list_of_files = ls(args.timeout)
    if list_of_files:
        print(args.delimiter.join(list_of_files))  # noqa: T201


def _handle_cp(args: argparse.Namespace) -> None:
    cp(args.src, args.dst, args.timeout)


def _handle_mv(args: argparse.Namespace) -> None:
    mv(args.src, args.dst, args.timeout)


def _handle_rm(args: argparse.Namespace) -> None:
    rm(args.paths, args.timeout)


def _handle_cat(args: argparse.Namespace) -> None:
    print(cat(args.path, args.timeout))  # noqa: T201


def _handle_du(args: argparse.Namespace) -> None:
    print(du(args.path, args.timeout))  # noqa: T201


def _handle_put(args: argparse.Namespace) -> None:
    put(args.path, args.target, args.timeout)


def _handle_get(args: argparse.Namespace) -> None:
    get(args.path, args.target, args.timeout)


def _handle_version(args: argparse.Namespace) -> None:
    version_info = version(args.timeout)
    for key, value in version_info.items():
        print(f"{key}: {value}")  # noqa: T201


def _build_parser() -> argparse.ArgumentParser:
    help_text = """
Interact with the filesystem on a connected the BBC micro:bit device.

The following commands are available:

* ls - list files on the device. Based on the equivalent Unix command.
* rm - remove a named file on the device. Based on the Unix command.
* cp - copy a file from one location to another on the device.
  Based on the Unix command.
* mv - move a file from one location to another on the device.
  Based on the Unix command.
* cat - display the contents of a file on the device.
  Based on the Unix command.
* du - get the size of a file on the device in bytes.
  Based on the Unix command.
* put - copy a named local file onto the device a la equivalent FTP command.
* get - copy a named file from the device to the local file system a la FTP.
* version - get version information for MicroPython running on the device.
"""
    parser = argparse.ArgumentParser(
        prog="ufs",
        description=help_text,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"microfs version: {importlib.metadata.version('microfs2')}",
        help="output version information of microfs and exit",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        help="Device response timeout in seconds.\nDefault to 10.",
        default=10,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", required=True
    )

    ls_parser = subparsers.add_parser(
        "ls", formatter_class=argparse.RawTextHelpFormatter
    )
    ls_parser.add_argument(
        "-d",
        "--delimiter",
        nargs="?",
        default=" ",
        help='Specify a delimiter string (default is whitespace). Eg. ";"',
    )

    rm_parser = subparsers.add_parser(
        "rm", formatter_class=argparse.RawTextHelpFormatter
    )
    rm_parser.add_argument(
        "paths", nargs="+", help="Specify one or more target filenames."
    )

    cp_parser = subparsers.add_parser(
        "cp", formatter_class=argparse.RawTextHelpFormatter
    )
    cp_parser.add_argument("src", help="Source filename on micro:bit.")
    cp_parser.add_argument("dst", help="Destination filename on micro:bit.")

    mv_parser = subparsers.add_parser(
        "mv", formatter_class=argparse.RawTextHelpFormatter
    )
    mv_parser.add_argument("src", help="Source filename on micro:bit.")
    mv_parser.add_argument("dst", help="Destination filename on micro:bit.")

    cat_parser = subparsers.add_parser(
        "cat", formatter_class=argparse.RawTextHelpFormatter
    )
    cat_parser.add_argument("path", help="The file to display.")

    du_parser = subparsers.add_parser(
        "du", formatter_class=argparse.RawTextHelpFormatter
    )
    du_parser.add_argument("path", help="The file to check du.")

    get_parser = subparsers.add_parser(
        "get", formatter_class=argparse.RawTextHelpFormatter
    )
    get_parser.add_argument(
        "path", help="The name of the file to copy from the micro:bit."
    )
    get_parser.add_argument(
        "target",
        type=pathlib.Path,
        nargs="?",
        help="The local file to copy the micro:bit file to.\n"
        "Defaults to the name of the file on the micro:bit.",
    )

    put_parser = subparsers.add_parser(
        "put", formatter_class=argparse.RawTextHelpFormatter
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

    subparsers.add_parser(
        "version", formatter_class=argparse.RawTextHelpFormatter
    )
    return parser


def _run_command(args: argparse.Namespace) -> None:
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
    except MicroBitNotFoundError as e:
        logger.error("The BBC micro:bit device is not connected: %s", e)  # noqa: TRY400
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)  # noqa: TRY400
    except IsADirectoryError as e:
        logger.error("Expected a file but found a directory: %s", e)  # noqa: TRY400
    except Exception:
        logger.exception("An unknown error occurred during execution.")


if __name__ == "__main__":  # pragma: no cover
    main()
