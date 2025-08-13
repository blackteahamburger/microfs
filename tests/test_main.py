# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
# Copyright (c) 2016 Nicholas H.Tollervey
#
# See the LICENSE file for more information.
"""Tests for the microfs.main module."""

from __future__ import annotations

import builtins
import pathlib
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest
import serial

from microfs.lib import MicroBitIOError, MicroBitNotFoundError
from microfs.main import main

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)  # pyright: ignore[reportUnknownMemberType]
def patch_importlib_metadata_version() -> Generator[None, Any]:
    """Fixture: patch importlib.metadata.version to return MICROFS_VERSION."""
    with mock.patch(
        "microfs.main.importlib.metadata.version", return_value="1.0.0"
    ):
        yield


def test_main_timeout() -> None:
    """Test that the default timeout is set to 10 seconds."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch("microfs.main.ls", return_value=["foo", "bar"]) as mock_ls,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch.object(builtins, "print") as mock_print,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_ls.assert_called_once_with(mock_serial_instance)
        mock_print.assert_called_once_with("foo bar")


def test_main_serial() -> None:
    """Test ls command with --serial flag passes MicroBitSerial."""
    with (
        mock.patch("sys.argv", ["ufs", "--serial", "/dev/ttyACM0", "ls"]),
        mock.patch("microfs.main.ls", return_value=["foo", "bar"]) as mock_ls,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch.object(builtins, "print") as mock_print,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_ls.assert_called_once_with(mock_serial_instance)
        mock_print.assert_called_once_with("foo bar")


def test_main_ls_no_files() -> None:
    """If the ls command is issued and no files exist, nothing is printed."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch("microfs.main.ls", return_value=[]) as mock_ls,
        mock.patch.object(builtins, "print") as mock_print,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_ls.assert_called_once_with(mock_serial_instance)
        mock_print.assert_not_called()


def test_main_rm() -> None:
    """
    If the rm command is correctly issued.

    Check the appropriate function is called.
    """
    with (
        mock.patch("sys.argv", ["ufs", "rm", "foo", "bar"]),
        mock.patch("microfs.main.rm", return_value=True) as mock_rm,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_rm.assert_called_once_with(mock_serial_instance, ["foo", "bar"])


def test_main_cp() -> None:
    """Test cp command calls cp function with correct arguments."""
    with (
        mock.patch("sys.argv", ["ufs", "cp", "foo.txt", "bar.txt"]),
        mock.patch("microfs.main.cp", return_value=True) as mock_cp,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_cp.assert_called_once_with(
            mock_serial_instance, "foo.txt", "bar.txt"
        )


def test_main_mv() -> None:
    """Test mv command calls mv function with correct arguments."""
    with (
        mock.patch("sys.argv", ["ufs", "mv", "foo.txt", "bar.txt"]),
        mock.patch("microfs.main.mv", return_value=True) as mock_mv,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_mv.assert_called_once_with(
            mock_serial_instance, "foo.txt", "bar.txt"
        )


def test_main_cat() -> None:
    """Test cat command calls cat function and prints the content."""
    with (
        mock.patch("sys.argv", ["ufs", "cat", "foo.txt"]),
        mock.patch("microfs.main.cat", return_value="filecontent") as mock_cat,
        mock.patch.object(builtins, "print") as mock_print,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_cat.assert_called_once_with(mock_serial_instance, "foo.txt")
        mock_print.assert_called_once_with("filecontent")


def test_main_du() -> None:
    """Test that the du command calls the du function and prints the result."""
    with (
        mock.patch("sys.argv", ["ufs", "du", "foo.txt"]),
        mock.patch("microfs.main.du", return_value=1024) as mock_du,
        mock.patch.object(builtins, "print") as mock_print,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_du.assert_called_once_with(mock_serial_instance, "foo.txt")
        mock_print.assert_called_once_with(1024)


def test_main_put() -> None:
    """
    If the put command is correctly issued.

    Check the appropriate function is called.
    """
    with (
        mock.patch("sys.argv", ["ufs", "put", "foo"]),
        mock.patch("microfs.main.put", return_value=True) as mock_put,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_put.assert_called_once_with(
            mock_serial_instance, pathlib.Path("foo"), None
        )


def test_main_get() -> None:
    """
    If the get command is correctly issued.

    Check the appropriate function is called.
    """
    with (
        mock.patch("sys.argv", ["ufs", "get", "foo"]),
        mock.patch("microfs.main.get", return_value=True) as mock_get,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_get.assert_called_once_with(mock_serial_instance, "foo", None)


def test_main_version() -> None:
    """Test main prints version info when 'version' command is used."""
    version_info = {"sysname": "microbit", "release": "1.0"}
    with (
        mock.patch("sys.argv", ["ufs", "version"]),
        mock.patch(
            "microfs.main.version", return_value=version_info
        ) as mock_version,
        mock.patch.object(builtins, "print") as mock_print,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_version.assert_called_once_with(mock_serial_instance)
        mock_print.assert_any_call(f"sysname: {version_info['sysname']}")
        mock_print.assert_any_call(f"release: {version_info['release']}")


def test_main_version_flag() -> None:
    """Test that main prints version when '--version' flag is used."""
    with (
        mock.patch("sys.argv", ["ufs", "--version"]),
        mock.patch("sys.stdout") as mock_stdout,
        pytest.raises(SystemExit) as pytest_exc,
    ):
        main()
    output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
    assert "MicroFS version: 1.0.0" in output
    assert pytest_exc.type is SystemExit


def test_main_version_micropython_option() -> None:
    """Test that main prints micropython version with '--micropython' used."""
    with (
        mock.patch("sys.argv", ["ufs", "version", "--micropython"]),
        mock.patch(
            "microfs.main.micropython_version", return_value="2.0.1"
        ) as mock_mp_ver,
        mock.patch.object(builtins, "print") as mock_print,
        mock.patch("microfs.main.MicroBitSerial") as mock_serial_class,
        mock.patch(
            "microfs.main.MicroBitSerial.get_serial",
            return_value=mock_serial_class.return_value,
        ),
    ):
        mock_serial_instance = mock_serial_class.return_value
        main()
        mock_mp_ver.assert_called_once_with(mock_serial_instance)
        mock_print.assert_called_once_with("2.0.1")


def test_main_handles_microbit_io_error() -> None:
    """Test that MicroBitIOError is logged as an I/O error."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch(
            "microfs.main._run_command", side_effect=MicroBitIOError("io fail")
        ),
        mock.patch("microfs.main.logging.getLogger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        with pytest.raises(SystemExit) as pytest_exc:
            main()
        mock_logger.error.assert_called_with(
            "An I/O error occurred with the BBC micro:bit device: %s", mock.ANY
        )
        assert "io fail" in str(mock_logger.error.call_args[0][1])
        assert pytest_exc.type is SystemExit


def test_main_handles_microbit_not_found_error() -> None:
    """Test that MicroBitNotFoundError is logged as device not connected."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch(
            "microfs.main._run_command",
            side_effect=MicroBitNotFoundError("not found"),
        ),
        mock.patch("microfs.main.logging.getLogger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        with pytest.raises(SystemExit) as pytest_exc:
            main()
        mock_logger.error.assert_called_with(
            "The BBC micro:bit device is not connected: %s", mock.ANY
        )
        assert "not found" in str(mock_logger.error.call_args[0][1])
        assert pytest_exc.type is SystemExit


def test_main_handles_file_not_found_error() -> None:
    """Test that FileNotFoundError is logged as file not found."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch(
            "microfs.main._run_command",
            side_effect=FileNotFoundError("missing.txt"),
        ),
        mock.patch("microfs.main.logging.getLogger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        with pytest.raises(SystemExit) as pytest_exc:
            main()
        mock_logger.error.assert_called_with("File not found: %s", mock.ANY)
        assert "missing.txt" in str(mock_logger.error.call_args[0][1])
        assert pytest_exc.type is SystemExit


def test_main_handles_is_a_directory_error() -> None:
    """Test that IsADirectoryError logs 'expected file but found directory'."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch(
            "microfs.main._run_command", side_effect=IsADirectoryError("dir")
        ),
        mock.patch("microfs.main.logging.getLogger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        with pytest.raises(SystemExit) as pytest_exc:
            main()
        mock_logger.error.assert_called_with(
            "Expected a file but found a directory: %s", mock.ANY
        )
        assert "dir" in str(mock_logger.error.call_args[0][1])
        assert pytest_exc.type is SystemExit


def test_main_handles_generic_exception() -> None:
    """Test that unknown exceptions are logged with logger.exception."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch(
            "microfs.main._run_command", side_effect=RuntimeError("boom")
        ),
        mock.patch("microfs.main.logging.getLogger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        with pytest.raises(SystemExit) as pytest_exc:
            main()
        mock_logger.exception.assert_called_with(
            "An unknown error occurred during execution."
        )
        assert pytest_exc.type is SystemExit


def test_main_handles_serial_exception() -> None:
    """Test that SerialException is logged as serial communication error."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch(
            "microfs.main._run_command",
            side_effect=serial.SerialException("fail"),
        ),
        mock.patch("microfs.main.logging.getLogger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        with pytest.raises(SystemExit) as pytest_exc:
            main()
        mock_logger.error.assert_called_with(
            "Serial communication error: %s", mock.ANY
        )
        assert "fail" in str(mock_logger.error.call_args[0][1])
        assert pytest_exc.type is SystemExit


def test_main_handles_serial_timeout_exception() -> None:
    """Test that SerialTimeoutException is logged as timeout."""
    with (
        mock.patch("sys.argv", ["ufs", "ls"]),
        mock.patch(
            "microfs.main._run_command",
            side_effect=serial.SerialTimeoutException("timeout"),
        ),
        mock.patch("microfs.main.logging.getLogger") as mock_get_logger,
    ):
        mock_logger = mock_get_logger.return_value
        with pytest.raises(SystemExit) as pytest_exc:
            main()
        mock_logger.error.assert_called_with(
            "Serial communication timed out: %s", mock.ANY
        )
        assert "timeout" in str(mock_logger.error.call_args[0][1])
        assert pytest_exc.type is SystemExit
