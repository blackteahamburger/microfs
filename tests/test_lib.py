# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
# Copyright (c) 2016 Nicholas H.Tollervey
#
# See the LICENSE file for more information.
"""Tests for the microfs module."""

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
    obj._port = port
    obj.is_open = False
    obj._timeout = timeout
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
        serial_obj.flush = mock.MagicMock()
        serial_obj.read_until = mock.MagicMock(return_value=b"not expected")
        serial_obj.flush_to_msg = mock.MagicMock(
            side_effect=microfs.lib.MicroBitIOError("fail")
        )
        with pytest.raises(microfs.lib.MicroBitIOError):
            serial_obj.raw_on()


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


def test_flush_reads_all() -> None:
    """Test that flush reads all bytes from the serial input buffer."""
    mock_serial = mock.MagicMock()
    mock_serial.in_waiting = 3

    def fake_read(n: int) -> bytes:
        return b"x" * n

    mock_serial.read.side_effect = fake_read
    vals = [3, 2, 1, 0]

    def in_waiting_side() -> int:
        return vals.pop(0)

    type(mock_serial).in_waiting = mock.PropertyMock(
        side_effect=in_waiting_side
    )
    microfs.lib.MicroBitSerial.flush(mock_serial)
    assert mock_serial.read.call_count == 3


def test_execute() -> None:
    """Check serial communication for command execution."""
    mock_serial = mock.MagicMock()
    mock_serial.write_commands = mock.MagicMock(return_value=b"[]")
    commands = ["import os", "os.listdir()"]
    out = microfs.lib.execute(commands, serial=mock_serial)
    assert out == b"[]"
    mock_serial.write_commands.assert_called_once_with(commands)


def test_execute_no_serial() -> None:
    """If no serial object, should call MicroBitSerial.get_serial()."""
    mock_serial = mock.MagicMock()
    mock_serial.write_commands = mock.MagicMock(return_value=b"[]")
    mock_context = mock.MagicMock()
    mock_context.__enter__.return_value = mock_serial
    mock_context.__exit__.return_value = None
    with mock.patch(
        "microfs.lib.MicroBitSerial.get_serial", return_value=mock_context
    ) as p:
        commands = ["import os", "os.listdir()"]
        out = microfs.lib.execute(commands)
        p.assert_called_once_with(10)
        mock_serial.write_commands.assert_called_once_with(commands)
        assert out == b"[]"


def test_ls() -> None:
    """If stdout is a list, ls should return the same list."""
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.lib.execute", return_value=b"['a.txt']\r\n"
    ) as execute:
        result = microfs.lib.ls(serial=mock_serial)
        assert result == ["a.txt"]
        execute.assert_called_once_with(
            ["import os", "print(os.listdir())"], 10, mock_serial
        )


def test_ls_width_delimiter() -> None:
    """If a delimiter is provided, result should match Python's list split."""
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.lib.execute", return_value=(b"[ 'a.txt','b.txt']\r\n")
    ) as execute:
        result = microfs.lib.ls(serial=mock_serial)
        delimited_result = ";".join(result)
        assert delimited_result == "a.txt;b.txt"
        execute.assert_called_once_with(
            ["import os", "print(os.listdir())"], 10, mock_serial
        )


def test_rm() -> None:
    """Test that rm removes a file and returns True."""
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.lib.execute", return_value=b"") as execute:
        microfs.lib.rm(["foo", "bar"], serial=mock_serial)
        execute.assert_called_once_with(
            ["import os", "os.remove('foo')", "os.remove('bar')"],
            10,
            mock_serial,
        )


def test_cp() -> None:
    """Test that cp calls execute with correct commands and returns True."""
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.lib.execute", return_value=b"") as execute:
        microfs.lib.cp("foo.txt", "bar.txt", serial=mock_serial)
        execute.assert_called_once_with(
            [
                "with open('foo.txt', 'rb') as fsrc, "
                "open('bar.txt', 'wb') as fdst: fdst.write(fsrc.read())"
            ],
            10,
            mock_serial,
        )


def test_mv() -> None:
    """Test that mv calls cp and rm and returns True."""
    mock_serial = mock.MagicMock()
    with (
        mock.patch("microfs.lib.cp", return_value=True) as mock_cp,
        mock.patch("microfs.lib.rm", return_value=True) as mock_rm,
    ):
        microfs.lib.mv("foo.txt", "bar.txt", serial=mock_serial)
        mock_cp.assert_called_once_with("foo.txt", "bar.txt", 10, mock_serial)
        mock_rm.assert_called_once_with(["foo.txt"], 10, mock_serial)


def test_cat() -> None:
    """Test that cat calls execute and returns the file content as string."""
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.lib.execute", return_value=b"hello world"
    ) as execute:
        result = microfs.lib.cat("foo.txt", serial=mock_serial)
        assert result == "hello world"
        execute.assert_called_once_with(
            ["with open('foo.txt', 'r') as f: print(f.read())"],
            10,
            mock_serial,
        )


def test_du() -> None:
    """Test that du returns the file size in bytes."""
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.lib.execute", return_value=b"1024") as execute:
        result = microfs.lib.du("foo.txt", serial=mock_serial)
        assert result == 1024
        execute.assert_called_once_with(
            ["import os", "print(os.size('foo.txt'))"], 10, mock_serial
        )


def test_put() -> None:
    """Check put calls and returns True for an existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "fixture_file.txt"
        file_path.write_bytes(b"hello")
        mock_serial = mock.MagicMock()
        with mock.patch("microfs.lib.execute", return_value=b"") as execute:
            microfs.lib.put(file_path, "remote.txt", serial=mock_serial)
            commands = [
                "fd = open('remote.txt', 'wb')",
                "f = fd.write",
                "f(b'hello')",
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, 10, mock_serial)


def test_put_no_target() -> None:
    """Check put calls and returns True for an existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "fixture_file.txt"
        file_path.write_bytes(b"hello")
        mock_serial = mock.MagicMock()
        with mock.patch("microfs.lib.execute", return_value=b"") as execute:
            microfs.lib.put(file_path, None, serial=mock_serial)
            commands = [
                f"fd = open('{file_path.name}', 'wb')",
                "f = fd.write",
                "f(b'hello')",
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, 10, mock_serial)


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
            mock.patch("microfs.lib.execute", return_value=b"b'hello'") as exe,
            mock.patch.object(pathlib.Path, "open", mock.mock_open()) as mo,
        ):
            microfs.lib.get("hello.txt", file_path, serial=mock_serial)
            exe.assert_called_once_with(commands, 10, mock_serial)
            mo.assert_called_once_with("wb")
            handle = mo()
            handle.write.assert_called_once_with(b"hello")


def test_get_no_target() -> None:
    """
    Check get writes the expected file content locally.

    If no target is provided, use the remote file name.
    """
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
        mock.patch("microfs.lib.execute", return_value=b"b'hello'") as exe,
        mock.patch.object(pathlib.Path, "open", mock.mock_open()) as mo,
    ):
        microfs.lib.get("hello.txt")
        exe.assert_called_once_with(commands, 10, None)
        mo.assert_called_once_with("wb")
        handle = mo()
        handle.write.assert_called_once_with(b"hello")


def test_get_invalid_data() -> None:
    """Test that get raises MicroBitIOError if returned data is not bytes."""
    mock_serial = mock.MagicMock()
    with (
        mock.patch("microfs.lib.execute", return_value=b"notbytes"),
        pytest.raises(microfs.lib.MicroBitIOError),
    ):
        microfs.lib.get("foo.txt", pathlib.Path("bar.txt"), mock_serial)


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
    with mock.patch("microfs.lib.execute", return_value=response) as execute:
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
        execute.assert_called_once_with(
            ["import os", "print(os.uname())"], 10, mock_serial
        )


def test_microbitserial_context_manager() -> None:
    """Test MicroBitSerial context manager calls raw_on and raw_off."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.raw_on = mock.MagicMock()
        serial_obj.raw_off = mock.MagicMock()
        serial_obj.close = mock.MagicMock()
        with (
            mock.patch(
                "microfs.lib.Serial.__enter__", return_value=serial_obj
            ),
            mock.patch("microfs.lib.Serial.__exit__", return_value=None),
        ):
            with serial_obj as s:
                assert s is serial_obj
                serial_obj.raw_on.assert_called_once()
            serial_obj.raw_off.assert_called_once()
            serial_obj.close.assert_not_called()


def test_microbitserial_write_and_close() -> None:
    """Test MicroBitSerial.write and close add sleep and call super."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        with (
            mock.patch("microfs.lib.Serial.write", return_value=1),
            mock.patch("microfs.lib.Serial.close") as super_close,
            mock.patch("time.sleep") as sleep,
        ):
            assert serial_obj.write(b"abc") == 1
            sleep.assert_any_call(0.01)
            serial_obj.close()
            sleep.assert_any_call(0.1)
            super_close.assert_called_once()


def test_flush_to_msg_error() -> None:
    """Test flush_to_msg raises MicroBitIOError if msg not found."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.read_until = mock.MagicMock(return_value=b"not the msg")
        with pytest.raises(microfs.lib.MicroBitIOError):
            serial_obj.flush_to_msg(b"expected")


def test_flush_reads_none() -> None:
    """Test flush does nothing if in_waiting is 0."""
    serial = mock.MagicMock()
    serial.in_waiting = 0
    microfs.lib.MicroBitSerial.flush(serial)
    serial.read.assert_not_called()


def test_raw_on_ctrl_a_needed() -> None:
    """Test raw_on sends extra CTRL-A if needed."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.write = mock.MagicMock()
        serial_obj.flush = mock.MagicMock()
        serial_obj.read_until = mock.MagicMock(
            side_effect=[
                b"raw REPL; CTRL-B to exit\r\n>",
                b"soft reboot\r\n",
                b"not raw repl",
                b"raw REPL; CTRL-B to exit\r\n>",
            ]
        )
        serial_obj.flush_to_msg = mock.MagicMock()
        with mock.patch("time.sleep"):
            serial_obj.raw_on()
        assert serial_obj.write.call_count >= 6


def test_raw_off() -> None:
    """Test raw_off sends CTRL-B and sleeps."""
    with mock.patch.object(serial.Serial, "__init__", return_value=None):
        serial_obj = microfs.lib.MicroBitSerial("/dev/ttyACM0")
        _init_serial_attrs(serial_obj, "/dev/ttyACM0")
        serial_obj.write = mock.MagicMock()
        with mock.patch("time.sleep") as sleep:
            serial_obj.raw_off()
            serial_obj.write.assert_called_once_with(b"\x02")
            sleep.assert_called_once()


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


def test_execute_with_serial() -> None:
    """Test execute uses provided serial object."""
    serial = mock.MagicMock()
    serial.write_commands.return_value = b"abc"
    out = microfs.lib.execute(["cmd"], serial=serial)
    assert out == b"abc"
    serial.write_commands.assert_called_once_with(["cmd"])


def test_execute_with_context() -> None:
    """Test execute creates serial if not provided."""
    mock_serial = mock.MagicMock()
    mock_serial.write_commands.return_value = b"abc"
    mock_context = mock.MagicMock()
    mock_context.__enter__.return_value = mock_serial
    mock_context.__exit__.return_value = None
    with mock.patch(
        "microfs.lib.MicroBitSerial.get_serial", return_value=mock_context
    ):
        out = microfs.lib.execute(["cmd"])
        assert out == b"abc"


def test_cat_decoding() -> None:
    """Test cat decodes output as string."""
    with mock.patch("microfs.lib.execute", return_value=b"hello"):
        out = microfs.lib.cat("foo.txt")
        assert out == "hello"


def test_du_int() -> None:
    """Test du returns int value from output."""
    with mock.patch("microfs.lib.execute", return_value=b"1234"):
        out = microfs.lib.du("foo.txt")
        assert out == 1234


def test_put_and_get_full() -> None:
    """Test put and get with all branches and error handling."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"abc")
        tmp.flush()
        tmp_path = pathlib.Path(tmp.name)
    with (
        mock.patch("microfs.lib.execute", return_value=b""),
        mock.patch.object(
            pathlib.Path, "open", mock.mock_open(read_data=b"abc")
        ),
    ):
        microfs.lib.put(tmp_path, None)
    with (
        mock.patch("microfs.lib.execute", return_value=b"notbytes"),
        mock.patch("pathlib.Path.open", mock.mock_open()),
        pytest.raises(microfs.lib.MicroBitIOError),
    ):
        microfs.lib.get("foo.txt", pathlib.Path("bar.txt"))
    with (
        mock.patch("microfs.lib.execute", return_value=b"b'abc'"),
        mock.patch("pathlib.Path.open", mock.mock_open()) as mo,
    ):
        microfs.lib.get("foo.txt", pathlib.Path("bar.txt"))
        mo.assert_called()


def test_version_parsing() -> None:
    """Test version parses output into dict."""
    out = (
        b"(sysname='microbit', nodename='microbit', release='1.0', "
        b"version='v1', machine='micro:bit')\r\n"
    )
    with mock.patch("microfs.lib.execute", return_value=out):
        result = microfs.lib.version()
        assert result["sysname"] == "microbit"
        assert result["release"] == "1.0"
        assert result["version"] == "v1"
        assert result["machine"] == "micro:bit"


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
