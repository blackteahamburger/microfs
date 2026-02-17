# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
#
# See the LICENSE file for more information.
"""Tests for lib.py with 100% coverage and comprehensive type hints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from microfs.lib import (
    MicroBitError,
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
    read_file,
    rm,
    version,
    write_file,
)

if TYPE_CHECKING:
    import pathlib


def _make_port(hwid: str) -> list[Any]:
    return ["PORT", "DESC", hwid]


def test_microbit_error_is_oserror() -> None:
    """MicroBitError must be a subclass of OSError."""
    assert isinstance(MicroBitError("boom"), OSError)


def test_microbit_io_error_hierarchy() -> None:
    """MicroBitIOError must be a subclass of MicroBitError."""
    assert isinstance(MicroBitIOError("io"), MicroBitError)


def test_microbit_not_found_error_hierarchy() -> None:
    """MicroBitNotFoundError must be a subclass of MicroBitError."""
    assert isinstance(MicroBitNotFoundError("not found"), MicroBitError)


def test_microbit_serial_baud_rate_constant() -> None:
    """SERIAL_BAUD_RATE must be set to 115200."""
    assert MicroBitSerial.SERIAL_BAUD_RATE == 115200


def test_microbit_serial_default_timeout_constant() -> None:
    """DEFAULT_TIMEOUT must be set to 10."""
    assert MicroBitSerial.DEFAULT_TIMEOUT == 10


def test_microbit_serial_init_calls_super() -> None:
    """MicroBitSerial.__init__ must delegate to Serial.__init__."""
    with patch("microfs.lib.Serial.__init__", return_value=None) as mock_init:
        serial: MagicMock = MagicMock(spec=MicroBitSerial)
        MicroBitSerial.__init__(serial, port="/dev/tty0", timeout=5.0)
        mock_init.assert_called_once()


def test_microbit_serial_init_with_defaults() -> None:
    """MicroBitSerial.__init__ must work when called with no arguments."""
    with patch("microfs.lib.Serial.__init__", return_value=None) as mock_init:
        serial: MagicMock = MagicMock(spec=MicroBitSerial)
        MicroBitSerial.__init__(serial)  # noqa: PLC2801
        mock_init.assert_called_once()


def test_find_microbit_found() -> None:
    """find_microbit returns port when VID/PID present."""
    ports: list[Any] = [_make_port("USB VID:PID=0D28:0204 SER=...")]
    with patch("microfs.lib.list_serial_ports", return_value=ports):
        result = MicroBitSerial.find_microbit()
    assert result is not None
    assert result[0] == "PORT"


def test_find_microbit_not_found_returns_none() -> None:
    """find_microbit must return None when no micro:bit VID/PID is present."""
    ports: list[Any] = [_make_port("USB VID:PID=1234:5678 SER=...")]
    with patch("microfs.lib.list_serial_ports", return_value=ports):
        assert MicroBitSerial.find_microbit() is None


def test_find_microbit_empty_list_returns_none() -> None:
    """find_microbit must return None when no serial ports are available."""
    with patch("microfs.lib.list_serial_ports", return_value=[]):
        assert MicroBitSerial.find_microbit() is None


def test_find_microbit_hwid_case_insensitive() -> None:
    """find_microbit must match the VID/PID regardless of case."""
    ports: list[Any] = [_make_port("usb vid:pid=0d28:0204")]
    with patch("microfs.lib.list_serial_ports", return_value=ports):
        assert MicroBitSerial.find_microbit() is not None


def test_get_serial_raises_when_not_found() -> None:
    """get_serial raises when device not found."""
    with (
        patch.object(MicroBitSerial, "find_microbit", return_value=None),
        pytest.raises(MicroBitNotFoundError, match="Could not find micro:bit"),
    ):
        MicroBitSerial.get_serial()


def test_get_serial_returns_serial_when_found() -> None:
    """get_serial must return a MicroBitSerial constructed from the detected port."""
    fake_port: list[str] = ["/dev/ttyACM0", "desc", "hwid"]
    mock_instance: MagicMock = MagicMock(spec=MicroBitSerial)
    with (
        patch.object(MicroBitSerial, "find_microbit", return_value=fake_port),
        patch.object(MicroBitSerial, "__new__", return_value=mock_instance) as mock_new,
    ):
        obj: MicroBitSerial = MicroBitSerial.get_serial(timeout=5)
        assert obj is mock_instance
        mock_new.assert_called_once_with(MicroBitSerial, "/dev/ttyACM0", timeout=5)


def test_open_calls_raw_on_and_import_os() -> None:
    """Open calls Serial.open and enables raw mode."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with (
        patch("microfs.lib.Serial.open") as mock_super_open,
        patch("microfs.lib.time.sleep") as mock_sleep,
    ):
        serial.raw_on = MagicMock()
        serial.write_command = MagicMock(return_value=b"")
        MicroBitSerial.open(serial)
    mock_super_open.assert_called_once()
    mock_sleep.assert_called_with(0.1)
    serial.raw_on.assert_called_once()
    serial.write_command.assert_called_once_with("import os")


def test_close_calls_raw_off_and_super() -> None:
    """Close must exit raw mode then call Serial.close."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with (
        patch("microfs.lib.Serial.close") as mock_super_close,
        patch("microfs.lib.time.sleep"),
    ):
        serial.raw_off = MagicMock()
        MicroBitSerial.close(serial)
    serial.raw_off.assert_called_once()
    mock_super_close.assert_called_once()


def test_close_suppresses_raw_off_exception() -> None:
    """Close must not propagate exceptions raised by raw_off."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.raw_off = MagicMock(side_effect=Exception("boom"))
    with (
        patch("microfs.lib.Serial.close") as mock_super_close,
        patch("microfs.lib.time.sleep"),
    ):
        MicroBitSerial.close(serial)
    mock_super_close.assert_called_once()


def test_write_calls_super_and_sleeps() -> None:
    """Write must delegate to Serial.write and sleep 10 ms afterward."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with (
        patch("microfs.lib.Serial.write", return_value=5) as mock_write,
        patch("microfs.lib.time.sleep") as mock_sleep,
    ):
        result: int | None = MicroBitSerial.write(serial, b"hello")
    assert result == 5
    mock_write.assert_called_once_with(b"hello")
    mock_sleep.assert_called_once_with(0.01)


def test_flush_to_msg_success() -> None:
    """flush_to_msg must not raise when the expected message is received."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    msg: bytes = b"raw REPL; CTRL-B to exit\r\n>"
    serial.read_until = MagicMock(return_value=msg)
    MicroBitSerial.flush_to_msg(serial, msg)


def test_flush_to_msg_failure_raises() -> None:
    """flush_to_msg raises if expected msg missing."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.read_until = MagicMock(return_value=b"something unexpected")
    with pytest.raises(MicroBitIOError, match="Could not enter raw REPL"):
        MicroBitSerial.flush_to_msg(serial, b"expected msg")


def test_raw_on_standard_path() -> None:
    """raw_on must complete successfully via the standard boot sequence."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    raw_repl_msg: bytes = b"raw REPL; CTRL-B to exit\r\n>"
    serial.read_until = MagicMock(
        side_effect=[raw_repl_msg, b"soft reboot\r\n", raw_repl_msg]
    )
    with patch("microfs.lib.time.sleep"):
        MicroBitSerial.raw_on(serial)
    assert serial.write.call_count >= 5


def test_raw_on_fallback_ctrl_a_path() -> None:
    """raw_on must re-send CTRL-A when the soft-reboot check fails to reach raw REPL."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    # The only real read_until call in raw_on is the if-not check at the bottom.
    # Returning something that does not end with raw_repl_msg triggers the branch.
    serial.read_until = MagicMock(return_value=b"something else")
    with patch("microfs.lib.time.sleep"):
        MicroBitSerial.raw_on(serial)
    assert serial.write.call_count >= 6


def test_raw_off_sends_ctrl_b_and_sleeps() -> None:
    """raw_off must send CTRL-B and sleep 100 ms."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with patch("microfs.lib.time.sleep") as mock_sleep:
        MicroBitSerial.raw_off(serial)
    serial.write.assert_called_once_with(b"\x02")
    mock_sleep.assert_called_once_with(0.1)


def test_write_command_success() -> None:
    """write_command must return the stdout bytes from the device."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.read_until = MagicMock(return_value=b"OKhello\x04\x04>")
    assert MicroBitSerial.write_command(serial, "print('hello')") == b"hello"


def test_write_command_stderr_raises() -> None:
    """write_command raises when device returns stderr."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    stderr: bytes = b"NameError: name 'x' is not defined\r\nNameError\r\n"
    serial.read_until = MagicMock(return_value=b"OK\x04" + stderr + b"\x04>")
    with pytest.raises(MicroBitIOError, match="NameError"):
        MicroBitSerial.write_command(serial, "x")


def test_write_command_stderr_no_newline_uses_raw_decoded() -> None:
    """write_command uses raw decoded string as error if no newline."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.read_until = MagicMock(return_value=b"OK\x04oops\x04>")
    with pytest.raises(MicroBitIOError, match="oops"):
        MicroBitSerial.write_command(serial, "bad")


def test_write_command_empty_stderr_msg_raises_generic() -> None:
    """write_command raises generic error when stderr empty."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.read_until = MagicMock(return_value=b"OK\x04\r\n\x04>")
    with pytest.raises(MicroBitIOError, match="There was an error"):
        MicroBitSerial.write_command(serial, "cmd")


def test_write_command_long_command_is_chunked() -> None:
    """Long commands are chunked into multiple writes."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.read_until = MagicMock(return_value=b"\x02out\x04\x04>")
    MicroBitSerial.write_command(serial, "x" * 100)
    data_writes = [c for c in serial.write.call_args_list if c[0][0] != b"\x04"]
    assert len(data_writes) > 1


def test_read_file_success_single_quote() -> None:
    """read_file must decode a b'...' response correctly."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"b'hello'")
    assert read_file(serial, "test.txt") == b"hello"


def test_read_file_success_double_quote() -> None:
    r"""read_file must decode a b\"...\" response correctly."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b'b"world"')
    assert read_file(serial, "test.txt") == b"world"


def test_read_file_invalid_format_raises() -> None:
    """read_file raises on unexpected device response."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"INVALID")
    with pytest.raises(MicroBitIOError, match="Unexpected file data format"):
        read_file(serial, "test.txt")


def test_read_file_invalid_no_start_raises() -> None:
    r"""read_file raises if response lacks expected start."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"x'hello'")
    with pytest.raises(MicroBitIOError):
        read_file(serial, "test.txt")


def test_read_file_invalid_no_end_raises() -> None:
    """read_file raises if response lacks end quote."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"b'hello")
    with pytest.raises(MicroBitIOError):
        read_file(serial, "test.txt")


def test_write_file_sends_correct_command() -> None:
    """write_file opens file in binary-write mode."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"")
    write_file(serial, "test.txt", b"data")
    cmd: str = serial.write_command.call_args[0][0]
    assert "test.txt" in cmd
    assert "wb" in cmd


def test_ls_returns_list() -> None:
    """Ls must parse the device output into a Python list of filenames."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"['a.py', 'b.txt']")
    assert ls(serial) == ["a.py", "b.txt"]


def test_ls_returns_empty_list() -> None:
    """Ls must return an empty list when there are no files on the device."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"[]")
    assert ls(serial) == []


def test_cp_reads_then_writes() -> None:
    """Cp reads source then writes dest."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with (
        patch("microfs.lib.read_file", return_value=b"content") as mock_read,
        patch("microfs.lib.write_file") as mock_write,
    ):
        cp(serial, "src.txt", "dst.txt")
    mock_read.assert_called_once_with(serial, "src.txt")
    mock_write.assert_called_once_with(serial, "dst.txt", b"content")


def test_mv_safe_copies_then_removes() -> None:
    """Mv (safe) copies then removes source."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with patch("microfs.lib.cp") as mock_cp, patch("microfs.lib.rm") as mock_rm:
        mv(serial, "src.txt", "dst.txt", unsafe=False)
    mock_cp.assert_called_once_with(serial, "src.txt", "dst.txt")
    mock_rm.assert_called_once_with(serial, ("src.txt",))


def test_mv_unsafe_removes_before_write() -> None:
    """Mv (unsafe) removes source before write."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with (
        patch("microfs.lib.read_file", return_value=b"data") as mock_read,
        patch("microfs.lib.rm") as mock_rm,
        patch("microfs.lib.write_file") as mock_write,
    ):
        mv(serial, "src.txt", "dst.txt", unsafe=True)
    mock_read.assert_called_once_with(serial, "src.txt")
    mock_rm.assert_called_once_with(serial, ("src.txt",))
    mock_write.assert_called_once_with(serial, "dst.txt", b"data")


def test_rm_single_file() -> None:
    """Rm must issue an os.remove command for a single file."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"")
    rm(serial, ["file.txt"])
    cmd: str = serial.write_command.call_args[0][0]
    assert "file.txt" in cmd
    assert "os.remove" in cmd


def test_rm_multiple_files_joined_with_newline() -> None:
    """Rm joins multiple os.remove calls with newlines."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"")
    rm(serial, ["a.py", "b.py"])
    cmd: str = serial.write_command.call_args[0][0]
    assert "a.py" in cmd
    assert "b.py" in cmd
    assert "\n" in cmd


def test_cat_returns_decoded_content() -> None:
    """Cat must return the file contents as a decoded string."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with patch("microfs.lib.read_file", return_value=b"hello world"):
        assert cat(serial, "test.txt") == "hello world"


def test_du_returns_int_size() -> None:
    """Du must return the file size as an integer number of bytes."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    serial.write_command = MagicMock(return_value=b"1024")
    assert du(serial, "big.bin") == 1024


def test_put_with_explicit_target(tmp_path: pathlib.Path) -> None:
    """Put writes local file to given target name on device."""
    local_file: pathlib.Path = tmp_path / "local.bin"
    local_file.write_bytes(b"\x00\x01\x02")
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with patch("microfs.lib.write_file") as mock_write:
        put(serial, local_file, "remote.bin")
    mock_write.assert_called_once_with(serial, "remote.bin", b"\x00\x01\x02")


def test_put_without_target_uses_local_filename(tmp_path: pathlib.Path) -> None:
    """Put uses local filename when no target given."""
    local_file: pathlib.Path = tmp_path / "myfile.py"
    local_file.write_bytes(b"print(1)")
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with patch("microfs.lib.write_file") as mock_write:
        put(serial, local_file, None)
    mock_write.assert_called_once_with(serial, "myfile.py", b"print(1)")


def test_get_no_target_writes_to_cwd() -> None:
    """Get writes to cwd if no target given."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with (
        patch("microfs.lib.read_file", return_value=b"data"),
        patch("pathlib.Path.write_bytes") as mock_wb,
    ):
        get(serial, "remote.txt", None)
    mock_wb.assert_called_once_with(b"data")


def test_get_with_directory_target(tmp_path: pathlib.Path) -> None:
    """Get places file in target dir using remote name."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    with patch("microfs.lib.read_file", return_value=b"data"):
        get(serial, "remote.txt", tmp_path)
    assert (tmp_path / "remote.txt").read_bytes() == b"data"


def test_get_with_file_target(tmp_path: pathlib.Path) -> None:
    """Get writes to exact target path when file given."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    target: pathlib.Path = tmp_path / "local_copy.txt"
    with patch("microfs.lib.read_file", return_value=b"bytes"):
        get(serial, "remote.txt", target)
    assert target.read_bytes() == b"bytes"


def test_version_parses_uname_output() -> None:
    """Version must parse the os.uname() output into a key/value dictionary."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    output: str = (
        "(sysname='microbit', nodename='microbit', "
        "release='2.1.0', version='micro:bit v2.1.0', machine='nRF52833')"
    )
    serial.write_command = MagicMock(return_value=output.encode())
    result: dict[str, str] = version(serial)
    assert result["sysname"] == "microbit"
    assert result["release"] == "2.1.0"


def test_micropython_version_new_style() -> None:
    """micropython_version returns release for new-style versions."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    version_info: dict[str, str] = {
        "sysname": "microbit",
        "nodename": "microbit",
        "release": "2.1.0",
        "version": "micro:bit v2.1.0 on 2022-12-01",
        "machine": "microbit with nRF52833",
    }
    with patch("microfs.lib.version", return_value=version_info):
        assert micropython_version(serial) == "2.1.0"


def test_micropython_version_old_style_returns_unknown() -> None:
    """micropython_version returns 'unknown' for old-style versions."""
    serial: MicroBitSerial = MagicMock(spec=MicroBitSerial)
    version_info: dict[str, str] = {
        "sysname": "microbit",
        "nodename": "microbit",
        "release": "1.0.0",
        "version": "MicroPython v1.13 on 2020-11-01",
        "machine": "BBC micro:bit v1",
    }
    with patch("microfs.lib.version", return_value=version_info):
        assert micropython_version(serial) == "unknown"
