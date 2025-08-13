# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
# Copyright (c) 2016 Nicholas H.Tollervey
#
# See the LICENSE file for more information.
"""Tests for the microfs.lib module."""

from __future__ import annotations

import pathlib
import tempfile
from typing import Any
from unittest import mock

import pytest
import serial

import microfs.lib


def _init_serial_attrs(
    obj: Any,  # noqa: ANN401
    port: str | None = None,
    timeout: int = 10,
) -> None:
    obj._port = port  # noqa: SLF001
    obj.is_open = False
    obj._timeout = timeout  # noqa: SLF001
    obj.timeout = timeout
    obj.portstr = port


def test_find_micro_bit() -> None:
    """
    Return the port and serial number if a micro:bit is connected.

    PySerial is used for detection.
    """

    class FakePort:
        """Pretends to be a representation of a port in PySerial."""

        def __init__(self, port_info: list[str], serial_number: str) -> None:
            self.port_info = port_info
            self.serial_number = serial_number

        def __getitem__(self, key: int) -> str:
            return self.port_info[key]

    serial_number = "9900023431864e45000e10050000005b00000000cc4d28bd"
    port_info = [
        "/dev/ttyACM3",
        "MBED CMSIS-DAP",
        "USB_CDC USB VID:PID=0D28:0204 "
        "SER=9900023431864e45000e10050000005b00000000cc4d28bd "
        "LOCATION=4-1.2",
    ]
    port = FakePort(port_info, serial_number)
    ports = [port]
    with mock.patch("microfs.lib.list_serial_ports", return_value=ports):
        result = microfs.lib.MicroBitSerial.find_microbit()
        assert result == port


def test_find_micro_bit_no_device() -> None:
    """Return None if no micro:bit is connected (PySerial)."""
    port = [
        "/dev/ttyACM3",
        "MBED NOT-MICROBIT",
        "USB_CDC USB VID:PID=0D29:0205 "
        "SER=9900023431864e45000e10050000005b00000000cc4d28de "
        "LOCATION=4-1.3",
    ]
    ports = [port]
    with mock.patch("microfs.lib.list_serial_ports", return_value=ports):
        result = microfs.lib.MicroBitSerial.find_microbit()
        assert result is None


def test_raw_on() -> None:
    """Check that raw mode commands are sent to the device."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.write = mock.MagicMock()
        serial_obj.reset_input_buffer = mock.MagicMock()
        serial_obj.flush = mock.MagicMock()
        serial_obj.read_until = mock.MagicMock()
        serial_obj.read_until.side_effect = [
            b"raw REPL; CTRL-B to exit\r\n>",
            b"soft reboot\r\n",
            b"raw REPL; CTRL-B to exit\r\n>",
        ]
        serial_obj.raw_on()
        assert serial_obj.write.call_count == 6
        assert serial_obj.write.call_args_list[0][0][0] == b"\x02"
        assert serial_obj.write.call_args_list[1][0][0] == b"\r\x03"
        assert serial_obj.write.call_args_list[2][0][0] == b"\r\x03"
        assert serial_obj.write.call_args_list[3][0][0] == b"\r\x03"
        assert serial_obj.write.call_args_list[4][0][0] == b"\r\x01"
        assert serial_obj.write.call_args_list[5][0][0] == b"\x04"
        assert serial_obj.read_until.call_count == 3
        assert (
            serial_obj.read_until.call_args_list[0][0][0]
            == b"raw REPL; CTRL-B to exit\r\n>"
        )
        assert (
            serial_obj.read_until.call_args_list[1][0][0] == b"soft reboot\r\n"
        )
        assert (
            serial_obj.read_until.call_args_list[2][0][0]
            == b"raw REPL; CTRL-B to exit\r\n>"
        )

        serial_obj.write.reset_mock()
        serial_obj.read_until.reset_mock()
        serial_obj.read_until.side_effect = [
            b"raw REPL; CTRL-B to exit\r\n>",
            b"soft reboot\r\n",
            b"foo\r\n",
            b"raw REPL; CTRL-B to exit\r\n>",
        ]
        serial_obj.raw_on()
        assert serial_obj.write.call_count == 7
        assert serial_obj.write.call_args_list[0][0][0] == b"\x02"
        assert serial_obj.write.call_args_list[1][0][0] == b"\r\x03"
        assert serial_obj.write.call_args_list[2][0][0] == b"\r\x03"
        assert serial_obj.write.call_args_list[3][0][0] == b"\r\x03"
        assert serial_obj.write.call_args_list[4][0][0] == b"\r\x01"
        assert serial_obj.write.call_args_list[5][0][0] == b"\x04"
        assert serial_obj.write.call_args_list[6][0][0] == b"\r\x01"
        assert serial_obj.read_until.call_count == 4
        assert (
            serial_obj.read_until.call_args_list[0][0][0]
            == b"raw REPL; CTRL-B to exit\r\n>"
        )
        assert (
            serial_obj.read_until.call_args_list[1][0][0] == b"soft reboot\r\n"
        )
        assert (
            serial_obj.read_until.call_args_list[2][0][0]
            == b"raw REPL; CTRL-B to exit\r\n>"
        )
        assert (
            serial_obj.read_until.call_args_list[3][0][0]
            == b"raw REPL; CTRL-B to exit\r\n>"
        )


def test_raw_on_fail() -> None:
    """Test that raw_on raises MicroBitIOError if prompt is not received."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.write = mock.MagicMock()
        serial_obj.reset_input_buffer = mock.MagicMock()
        serial_obj.flush = mock.MagicMock()
        serial_obj.read_until = mock.MagicMock(return_value=b"not expected")
        serial_obj.flush_to_msg = mock.MagicMock(
            side_effect=microfs.lib.MicroBitIOError("fail")
        )
        with pytest.raises(microfs.lib.MicroBitIOError):
            serial_obj.raw_on()


def test_raw_off() -> None:
    """Test raw_off sends CTRL-B and sleeps."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.write = mock.MagicMock()
        with mock.patch("time.sleep") as sleep:
            serial_obj.raw_off()
            serial_obj.write.assert_called_once_with(b"\x02")
            sleep.assert_called()


def test_flush_to_msg_success() -> None:
    """Test flush_to_msg succeeds if expected message is received."""
    mock_serial = mock.MagicMock()
    msg = b"raw REPL; CTRL-B to exit\r\n>"
    mock_serial.read_until.return_value = msg
    microfs.lib.MicroBitSerial.flush_to_msg(mock_serial, msg)
    mock_serial.read_until.assert_called_once_with(msg)


def test_flush_to_msg_failure() -> None:
    """Test that flush_to_msg raises MicroBitIOError if no message."""
    mock_serial = mock.MagicMock()
    msg = b"raw REPL; CTRL-B to exit\r\n>"
    mock_serial.read_until.return_value = b"something else"
    with pytest.raises(microfs.lib.MicroBitIOError):
        microfs.lib.MicroBitSerial.flush_to_msg(mock_serial, msg)


def test_ls() -> None:
    """If stdout is a list, ls should return the same list."""
    mock_serial = mock.MagicMock()
    with mock.patch.object(
        mock_serial, "write_commands", return_value=b"['a.txt']\r\n"
    ) as write_commands:
        result = microfs.lib.ls(mock_serial)
        assert result == ["a.txt"]
        write_commands.assert_called_once_with([
            "import os",
            "print(os.listdir())",
        ])


def test_ls_width_delimiter() -> None:
    """If a delimiter is provided, result should match Python's list split."""
    mock_serial = mock.MagicMock()
    with mock.patch.object(
        mock_serial, "write_commands", return_value=(b"[ 'a.txt','b.txt']\r\n")
    ) as write_commands:
        result = microfs.lib.ls(serial=mock_serial)
        delimited_result = ";".join(result)
        assert delimited_result == "a.txt;b.txt"
        write_commands.assert_called_once_with([
            "import os",
            "print(os.listdir())",
        ])


def test_rm() -> None:
    """Test that rm removes a file."""
    mock_serial = mock.MagicMock()
    with mock.patch.object(
        mock_serial, "write_commands", return_value=b""
    ) as write_commands:
        microfs.lib.rm(mock_serial, ["foo.txt"])
        write_commands.assert_called_once_with([
            "import os",
            "os.remove('foo.txt')",
        ])


def test_cp() -> None:
    """Test that cp calls execute with correct commands."""
    mock_serial = mock.MagicMock()
    with mock.patch.object(
        mock_serial, "write_commands", return_value=b""
    ) as write_commands:
        microfs.lib.cp(mock_serial, "foo.txt", "bar.txt")
        write_commands.assert_called_once_with([
            "with open('foo.txt', 'rb') as fsrc, "
            "open('bar.txt', 'wb') as fdst: fdst.write(fsrc.read())"
        ])


def test_mv() -> None:
    """Test that mv calls cp and rm."""
    mock_serial = mock.MagicMock()
    with (
        mock.patch("microfs.lib.cp") as mock_cp,
        mock.patch("microfs.lib.rm") as mock_rm,
    ):
        microfs.lib.mv(mock_serial, "foo.txt", "bar.txt")
        mock_cp.assert_called_once_with(mock_serial, "foo.txt", "bar.txt")
        mock_rm.assert_called_once_with(mock_serial, ["foo.txt"])


def test_cat() -> None:
    """Test that cat calls execute and returns the file content as string."""
    mock_serial = mock.MagicMock()
    with mock.patch.object(
        mock_serial, "write_commands", return_value=b"hello world"
    ) as write_commands:
        result = microfs.lib.cat(mock_serial, "foo.txt")
        assert result == "hello world"
        write_commands.assert_called_once_with([
            "with open('foo.txt', 'r') as f: print(f.read())"
        ])


def test_du() -> None:
    """Test that du returns the file size in bytes."""
    mock_serial = mock.MagicMock()
    with mock.patch.object(
        mock_serial, "write_commands", return_value=b"1024"
    ) as write_commands:
        result = microfs.lib.du(mock_serial, "foo.txt")
        assert result == 1024
        write_commands.assert_called_once_with([
            "import os",
            "print(os.size('foo.txt'))",
        ])


def test_put() -> None:
    """Check put calls for an existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "fixture_file.txt"
        file_path.write_bytes(b"hello")
        mock_serial = mock.MagicMock()
        with mock.patch.object(
            mock_serial, "write_commands", return_value=b""
        ) as write_commands:
            microfs.lib.put(mock_serial, file_path, "remote.txt")
            commands = [
                "fd = open('remote.txt', 'wb')",
                "f = fd.write",
                "f(b'hello')",
                "fd.close()",
            ]
            write_commands.assert_called_once_with(commands)


def test_put_no_target() -> None:
    """Check put calls for an existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "fixture_file.txt"
        file_path.write_bytes(b"hello")
        mock_serial = mock.MagicMock()
        with mock.patch.object(
            mock_serial, "write_commands", return_value=b""
        ) as write_commands:
            microfs.lib.put(mock_serial, file_path, None)
            commands = [
                f"fd = open('{file_path.name}', 'wb')",
                "f = fd.write",
                "f(b'hello')",
                "fd.close()",
            ]
            write_commands.assert_called_once_with(commands)


def test_get() -> None:
    """Check get writes the expected file content locally."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "local.txt"
        mock_serial = mock.MagicMock()
        commands = [
            "\n".join([
                "try:",
                " from microbit import uart as u",
                "except ImportError:",
                " try:",
                "  from machine import UART",
                "  u = UART(0, "
                f"{microfs.lib.MicroBitSerial.SERIAL_BAUD_RATE})",
                " except Exception:",
                "  try:",
                "   from sys import stdout as u",
                "  except Exception:",
                "   raise Exception('Could not find UART module in device.')",
            ]),
            "f = open('hello.txt', 'rb')",
            "r = f.read",
            "result = True",
            "while result:\n result = r(32)\n"
            " if result:\n  u.write(repr(result))",
            "f.close()",
        ]
        with (
            mock.patch.object(
                mock_serial, "write_commands", return_value=b"b'hello'"
            ) as write_commands,
            mock.patch.object(pathlib.Path, "write_bytes") as write_bytes,
        ):
            microfs.lib.get(mock_serial, "hello.txt", file_path)
            write_commands.assert_called_once_with(commands)
            write_bytes.assert_called_once_with(b"hello")


def test_get_no_target() -> None:
    """
    Check get writes the expected file content locally.

    If no target is provided, use the remote file name.
    """
    mock_serial = mock.MagicMock()
    commands = [
        "\n".join([
            "try:",
            " from microbit import uart as u",
            "except ImportError:",
            " try:",
            "  from machine import UART",
            f"  u = UART(0, {microfs.lib.MicroBitSerial.SERIAL_BAUD_RATE})",
            " except Exception:",
            "  try:",
            "   from sys import stdout as u",
            "  except Exception:",
            "   raise Exception('Could not find UART module in device.')",
        ]),
        "f = open('hello.txt', 'rb')",
        "r = f.read",
        "result = True",
        "while result:\n result = r(32)\n if result:\n  u.write(repr(result))",
        "f.close()",
    ]
    with (
        mock.patch.object(
            mock_serial, "write_commands", return_value=b"b'hello'"
        ) as write_commands,
        mock.patch.object(pathlib.Path, "write_bytes") as write_bytes,
    ):
        microfs.lib.get(mock_serial, "hello.txt")
        write_commands.assert_called_once_with(commands)
        write_bytes.assert_called_once_with(b"hello")


def test_get_target_is_dir() -> None:
    """
    Check get writes the expected file content when target is a directory.

    Should save as target/filename.
    """
    mock_serial = mock.MagicMock()
    commands = [
        "\n".join([
            "try:",
            " from microbit import uart as u",
            "except ImportError:",
            " try:",
            "  from machine import UART",
            f"  u = UART(0, {microfs.lib.MicroBitSerial.SERIAL_BAUD_RATE})",
            " except Exception:",
            "  try:",
            "   from sys import stdout as u",
            "  except Exception:",
            "   raise Exception('Could not find UART module in device.')",
        ]),
        "f = open('hello.txt', 'rb')",
        "r = f.read",
        "result = True",
        "while result:\n result = r(32)\n if result:\n  u.write(repr(result))",
        "f.close()",
    ]
    with (
        tempfile.TemporaryDirectory() as tmpdir,
        mock.patch.object(
            mock_serial, "write_commands", return_value=b"b'hello'"
        ) as write_commands,
        mock.patch.object(pathlib.Path, "write_bytes") as write_bytes,
        mock.patch.object(pathlib.Path, "is_dir", return_value=True),
    ):
        target_dir = pathlib.Path(tmpdir)
        microfs.lib.get(mock_serial, "hello.txt", target_dir)
        write_commands.assert_called_once_with(commands)
        write_bytes.assert_called_once_with(b"hello")


def test_get_invalid_data() -> None:
    """Test that get raises MicroBitIOError if returned data is not bytes."""
    mock_serial = mock.MagicMock()
    with (
        mock.patch.object(
            mock_serial, "write_commands", return_value=b"notbytes"
        ),
        pytest.raises(microfs.lib.MicroBitIOError),
    ):
        microfs.lib.get(mock_serial, "foo.txt", pathlib.Path("bar.txt"))


def test_version() -> None:
    """Check version returns expected result for valid device response."""
    response = (
        b"(sysname='microbit', nodename='microbit', "
        b"release='1.0', "
        b"version=\"micro:bit v1.0-b'e10a5ff' on 2018-6-8; "
        b'MicroPython v1.9.2-34-gd64154c73 on 2017-09-01", '
        b"machine='micro:bit with nRF51822')\r\n"
    )
    mock_serial = mock.MagicMock()
    with mock.patch.object(
        mock_serial, "write_commands", return_value=response
    ) as write_commands:
        result = microfs.lib.version(serial=mock_serial)
        assert result["sysname"] == "microbit"
        assert result["nodename"] == "microbit"
        assert result["release"] == "1.0"
        assert result["version"] == (
            "micro:bit v1.0-b'e10a5ff' on "
            "2018-6-8; "
            "MicroPython v1.9.2-34-gd64154c73 on "
            "2017-09-01"
        )
        assert result["machine"] == "micro:bit with nRF51822"
        write_commands.assert_called_once_with([
            "import os",
            "print(os.uname())",
        ])


def test_micropython_version_new_style() -> None:
    """Test micropython_version returns the new style version string."""
    mock_serial = mock.MagicMock()
    version_dict = {
        "sysname": "microbit",
        "nodename": "microbit",
        "release": "2.1.2",
        "version": "micro:bit v2.1.2+3f22f30-dirty on 2025-08-10; "
        "MicroPython v1.27.0-preview on 2025-08-10",
        "machine": "micro:bit with nRF52833",
    }
    with mock.patch("microfs.lib.version", return_value=version_dict):
        result = microfs.lib.micropython_version(mock_serial)
        assert result == "2.1.2"


def test_micropython_version_old_style() -> None:
    """Test micropython_version returns unknown for old version string."""
    mock_serial = mock.MagicMock()
    version_dict = {
        "sysname": "microbit",
        "nodename": "microbit",
        "release": "1.0",
        "version": "MicroPython v1.8.1",
        "machine": "micro:bit with nRF51822",
    }
    with mock.patch("microfs.lib.version", return_value=version_dict):
        result = microfs.lib.micropython_version(mock_serial)
        assert result == "unknown"


def test_write_command_error() -> None:
    """Test write_command raises MicroBitIOError if error in response."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.write = mock.MagicMock()
        serial_obj.read_until = mock.MagicMock(
            return_value=b"OK\x04error\x04>"
        )
        with pytest.raises(microfs.lib.MicroBitIOError):
            serial_obj.write_command("os.listdir()")


def test_write_commands() -> None:
    """Test write_commands sends all commands and returns result."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.write = mock.MagicMock()
        serial_obj.read_until = mock.MagicMock(
            side_effect=[b"OK\x04\x04>", b"OK[]\x04\x04>"]
        )
        out = serial_obj.write_commands(["import os", "os.listdir()"])
        assert out == b"[]"
        assert serial_obj.write.call_count >= 3


def test_get_serial_success() -> None:
    """Test get_serial returns MicroBitSerial if device found."""
    port = (
        "/dev/ttyACM0",
        "MBED CMSIS-DAP",
        "USB_CDC USB VID:PID=0D28:0204 ...",
    )
    with (
        mock.patch(
            "microfs.lib.MicroBitSerial.find_microbit", return_value=port
        ),
        mock.patch.object(serial.Serial, "__init__", return_value=None),
    ):
        serial_obj = microfs.lib.MicroBitSerial.get_serial(timeout=5)
        _init_serial_attrs(serial_obj, "/dev/ttyACM0", 5)
        assert isinstance(serial_obj, microfs.lib.MicroBitSerial)
        assert serial_obj.port == "/dev/ttyACM0"
        assert serial_obj.timeout == 5


def test_get_serial_not_found() -> None:
    """Test get_serial raises MicroBitNotFoundError if no device found."""
    with mock.patch(
        "microfs.lib.MicroBitSerial.find_microbit", return_value=None
    ):
        with pytest.raises(microfs.lib.MicroBitNotFoundError) as exc:
            microfs.lib.MicroBitSerial.get_serial()
        assert "Could not find micro:bit" in str(exc.value)


def test_write() -> None:
    """Test that write calls super().write and sleeps briefly."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        with (
            mock.patch.object(
                serial.Serial, "write", return_value=5
            ) as super_write,
            mock.patch("time.sleep") as sleep,
        ):
            result = serial_obj.write(b"abc")
            super_write.assert_called_once_with(b"abc")
            sleep.assert_called_once_with(0.01)
            assert result == 5


def test_open() -> None:
    """Test that open calls super().open, sleeps, and raw_on."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        with (
            mock.patch.object(serial.Serial, "open") as super_open,
            mock.patch("time.sleep") as sleep,
            mock.patch.object(serial_obj, "raw_on") as raw_on,
        ):
            serial_obj.open()
            super_open.assert_called_once_with()
            sleep.assert_any_call(0.1)
            raw_on.assert_called_once_with()


def test_close() -> None:
    """Test that close calls raw_off, super().close, and sleeps."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        with (
            mock.patch.object(serial_obj, "raw_off") as raw_off,
            mock.patch.object(serial.Serial, "close") as super_close,
            mock.patch("time.sleep") as sleep,
        ):
            serial_obj.close()
            raw_off.assert_called_once_with()
            super_close.assert_called_once_with()
            sleep.assert_any_call(0.1)


def test_close_suppresses_raw_off_exception() -> None:
    """Test that close suppresses exceptions from raw_off."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        with (
            mock.patch.object(
                serial_obj, "raw_off", side_effect=Exception("fail")
            ),
            mock.patch.object(serial.Serial, "close") as super_close,
            mock.patch("time.sleep") as sleep,
        ):
            serial_obj.close()
            super_close.assert_called_once_with()
            sleep.assert_any_call(0.1)
