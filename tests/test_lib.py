# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
# Copyright (c) 2016 Nicholas H.Tollervey
#
# See the LICENSE file for more information.
"""Tests for the microfs module."""

import pathlib
import tempfile
from unittest import mock

import pytest

import microfs.lib

MICROFS_VERSION = "1.2.3"


def test_find_micro_bit() -> None:
    """
    If a micro:bit is connected (according to PySerial) return the port and
    serial number.
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
        result = microfs.lib.find_microbit()
        assert result == ("/dev/ttyACM3", serial_number)


def test_find_micro_bit_no_device() -> None:
    """If there is no micro:bit connected (according to PySerial) return None."""
    port = [
        "/dev/ttyACM3",
        "MBED NOT-MICROBIT",
        "USB_CDC USB VID:PID=0D29:0205 "
        "SER=9900023431864e45000e10050000005b00000000cc4d28de "
        "LOCATION=4-1.3",
    ]
    ports = [port]
    with mock.patch("microfs.lib.list_serial_ports", return_value=ports):
        result = microfs.lib.find_microbit()
        assert result == (None, None)


def test_raw_on() -> None:
    """
    Check the expected commands are sent to the device to put MicroPython into
    raw mode.
    """
    mock_serial = mock.MagicMock()
    mock_serial.in_waiting = 0
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n",
        b"raw REPL; CTRL-B to exit\r\n>",
    ]
    mock_serial.read_until.side_effect = data
    microfs.lib.raw_on(mock_serial)
    assert mock_serial.write.call_count == 6
    assert mock_serial.write.call_args_list[0][0][0] == b"\x02"
    assert mock_serial.write.call_args_list[1][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[2][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[3][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[4][0][0] == b"\r\x01"
    assert mock_serial.write.call_args_list[5][0][0] == b"\x04"
    assert mock_serial.read_until.call_count == 3
    assert mock_serial.read_until.call_args_list[0][0][0] == data[0]
    assert mock_serial.read_until.call_args_list[1][0][0] == data[1]
    assert mock_serial.read_until.call_args_list[2][0][0] == data[2]

    mock_serial.reset_mock()
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n",
        b"foo\r\n",
        b"raw REPL; CTRL-B to exit\r\n>",
    ]
    mock_serial.read_until.side_effect = data
    microfs.lib.raw_on(mock_serial)
    assert mock_serial.write.call_count == 7
    assert mock_serial.write.call_args_list[0][0][0] == b"\x02"
    assert mock_serial.write.call_args_list[1][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[2][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[3][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[4][0][0] == b"\r\x01"
    assert mock_serial.write.call_args_list[5][0][0] == b"\x04"
    assert mock_serial.write.call_args_list[6][0][0] == b"\r\x01"
    assert mock_serial.read_until.call_count == 4
    assert mock_serial.read_until.call_args_list[0][0][0] == data[0]
    assert mock_serial.read_until.call_args_list[1][0][0] == data[1]
    assert mock_serial.read_until.call_args_list[2][0][0] == data[3]
    assert mock_serial.read_until.call_args_list[3][0][0] == data[3]


def test_raw_on_and_off() -> None:
    """Test that raw_on sends the correct sequence and raw_off exits raw mode."""
    mock_serial = mock.MagicMock()
    mock_serial.in_waiting = 0
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n",
        b"raw REPL; CTRL-B to exit\r\n>",
    ]
    mock_serial.read_until.side_effect = data
    microfs.lib.raw_on(mock_serial)
    assert mock_serial.write.call_count >= 6
    microfs.lib.raw_off(mock_serial)
    mock_serial.write.assert_called_with(b"\x02")


def test_raw_on_fail() -> None:
    """Test that raw_on raises MicroBitIOError if the expected prompt is not received."""
    mock_serial = mock.MagicMock()
    mock_serial.in_waiting = 0
    mock_serial.read_until.side_effect = [b"not expected"]
    with pytest.raises(microfs.lib.MicroBitIOError):
        microfs.lib.raw_on(mock_serial)


def test_flush_to_msg_success() -> None:
    """Test that flush_to_msg does not raise when the expected message is received."""
    mock_serial = mock.MagicMock()
    msg = b"raw REPL; CTRL-B to exit\r\n>"
    mock_serial.read_until.return_value = msg
    microfs.lib.flush_to_msg(mock_serial, msg)
    mock_serial.read_until.assert_called_once_with(msg)


def test_flush_to_msg_failure() -> None:
    """Test that flush_to_msg raises MicroBitIOError when the expected message is not received."""
    mock_serial = mock.MagicMock()
    msg = b"raw REPL; CTRL-B to exit\r\n>"
    mock_serial.read_until.return_value = b"something else"
    with pytest.raises(microfs.lib.MicroBitIOError):
        microfs.lib.flush_to_msg(mock_serial, msg)


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
    microfs.lib.flush(mock_serial)
    assert mock_serial.read.call_count == 3


def test_get_serial() -> None:
    """
    Ensure that if a port is found then PySerial is used to create a connection
    to the device.
    """
    mock_serial = mock.MagicMock()
    mock_result = (
        "/dev/ttyACM3",
        "9900000031864e45003c10070000006e0000000097969901",
    )
    with (
        mock.patch("microfs.lib.find_microbit", return_value=mock_result),
        mock.patch("microfs.lib.Serial", return_value=mock_serial),
    ):
        result = microfs.lib.get_serial(10)
        assert result == mock_serial


def test_get_serial_no_port() -> None:
    """An MicroBitNotFoundError should be raised if no micro:bit is found."""
    with (
        mock.patch("microfs.lib.find_microbit", return_value=(None, None)),
        pytest.raises(microfs.lib.MicroBitNotFoundError) as ex,
    ):
        microfs.lib.get_serial()
    assert ex.value.args[0] == "Could not find micro:bit."


def test_execute() -> None:
    """
    Ensure that the expected communication happens via the serial connection
    with the connected micro:bit to facilitate the execution of the passed
    in command.
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(
        side_effect=[b"OK\x04\x04>", b"OK[]\x04\x04>"]
    )
    commands = ["import os", "os.listdir()"]
    with (
        mock.patch("microfs.lib.get_serial", return_value=mock_serial),
        mock.patch("microfs.lib.raw_on", return_value=None) as raw_mon,
        mock.patch("microfs.lib.raw_off", return_value=None) as raw_moff,
    ):
        out = microfs.lib.execute(commands, mock_serial)
        assert out == b"[]"
        raw_mon.assert_called_once_with(mock_serial)
        raw_moff.assert_called_once_with(mock_serial)
        # Check the writes are of the right number and sort (to ensure the
        # device is put into the correct states).
        assert mock_serial.write.call_count == 4
        encoded0 = commands[0].encode()
        encoded1 = commands[1].encode()
        assert mock_serial.write.call_args_list[0][0][0] == encoded0
        assert mock_serial.write.call_args_list[1][0][0] == b"\x04"
        assert mock_serial.write.call_args_list[2][0][0] == encoded1
        assert mock_serial.write.call_args_list[3][0][0] == b"\x04"


def test_execute_raises_on_err_bytes() -> None:
    """Test that execute raises MicroBitIOError if err is not empty."""
    mock_serial = mock.MagicMock()
    mock_serial.read_until.return_value = b"OK\x04out\x04err\x04>"
    with (
        mock.patch("microfs.lib.get_serial", return_value=mock_serial),
        mock.patch("microfs.lib.raw_on", return_value=None),
        mock.patch("microfs.lib.raw_off", return_value=None),
        mock.patch(
            "microfs.lib.clean_error", return_value="errormsg"
        ) as mock_clean_error,
        pytest.raises(microfs.lib.MicroBitIOError) as excinfo,
    ):
        microfs.lib.execute(["cmd"], mock_serial)
    assert "errormsg" in str(excinfo.value)
    mock_clean_error.assert_called_once()


def test_execute_no_serial() -> None:
    """
    Ensure that if there's no serial object passed into the execute method, it
    attempts to get_serial().
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(
        side_effect=[b"OK\x04\x04>", b"OK[]\x04\x04>"]
    )
    commands = ["import os", "os.listdir()"]
    with (
        mock.patch("microfs.lib.get_serial", return_value=mock_serial) as p,
        mock.patch("microfs.lib.raw_on", return_value=None),
        mock.patch("microfs.lib.raw_off", return_value=None),
    ):
        _ = microfs.lib.execute(commands)
        p.assert_called_once_with(10)
        mock_serial.close.assert_called_once_with()


def test_clean_error() -> None:
    """
    Check that given some bytes (derived from stderr) are turned into a
    readable error message: we're only interested in getting the error message
    from the exception, so it's important to strip away all the potentially
    confusing stack trace if it exists.
    """
    msg = (
        b"Traceback (most recent call last):\r\n "
        b'File "<stdin>", line 2, in <module>\r\n'
        b'File "<stdin>", line 2, in <module>\r\n'
        b'File "<stdin>", line 2, in <module>\r\n'
        b"OSError: file not found\r\n"
    )
    result = microfs.lib.clean_error(msg)
    assert result == "OSError: file not found"


def test_clean_error_no_stack_trace() -> None:
    """
    Sometimes stderr may not conform to the expected stacktrace structure. In
    which case, just return a string version of the message.
    """
    msg = b"This does not conform!"
    assert microfs.lib.clean_error(msg) == "This does not conform!"


def test_clean_error_but_no_error() -> None:
    """
    Worst case, the function has been called with empty bytes so return a
    vague message.
    """
    assert microfs.lib.clean_error(b"") == "There was an error."


def test_ls() -> None:
    """
    If a list is returned as a result in stdout, ensure that the equivalent
    Python list is returned from ls.
    """
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
    """
    If a delimiter is provided, ensure that the result from stdout is
    equivalent to the list returned by Python.
    """
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
                "with open('foo.txt', 'rb') as fsrc, open('bar.txt', 'wb') as fdst: fdst.write(fsrc.read())"
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
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True.
    """
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
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True.
    """
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
    """
    Ensure a successful get results in the expected file getting written on
    the local file system with the expected content.
    """
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
                f"  u = UART(0, {microfs.lib.SERIAL_BAUD_RATE})",
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
            microfs.lib.get("hello.txt", file_path, serial=mock_serial)
            exe.assert_called_once_with(commands, 10, mock_serial)
            mo.assert_called_once_with("wb")
            handle = mo()
            handle.write.assert_called_once_with(b"hello")


def test_get_no_target() -> None:
    """
    Ensure a successful get results in the expected file getting written on
    the local file system with the expected content. In this case, since no
    target is provided, use the name of the remote file.
    """
    commands = [
        "\n".join([
            "try:",
            " from microbit import uart as u",
            "except ImportError:",
            " try:",
            "  from machine import UART",
            f"  u = UART(0, {microfs.lib.SERIAL_BAUD_RATE})",
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
    """Test that get raises MicroBitIOError if the returned data is not valid bytes."""
    mock_serial = mock.MagicMock()
    with (
        mock.patch("microfs.lib.execute", return_value=b"notbytes"),
        pytest.raises(microfs.lib.MicroBitIOError),
    ):
        microfs.lib.get("foo.txt", pathlib.Path("bar.txt"), mock_serial)


def test_version() -> None:
    """
    Ensure the version method returns the expected result when the response
    from the device is the expected bytes.
    """
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
