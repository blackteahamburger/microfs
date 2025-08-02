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
"""Tests for the microfs module."""

import pathlib
import tempfile
from unittest import mock

import pytest

import microfs
from microfs import SERIAL_BAUD_RATE, MicroBitIOError, MicroBitNotFoundError

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
    with mock.patch("microfs.list_serial_ports", return_value=ports):
        result = microfs.find_microbit()
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
    with mock.patch("microfs.list_serial_ports", return_value=ports):
        result = microfs.find_microbit()
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
    microfs.raw_on(mock_serial)
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
    microfs.raw_on(mock_serial)
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
    microfs.raw_on(mock_serial)
    assert mock_serial.write.call_count >= 6
    microfs.raw_off(mock_serial)
    mock_serial.write.assert_called_with(b"\x02")


def test_raw_on_fail() -> None:
    """Test that raw_on raises MicroBitIOError if the expected prompt is not received."""
    mock_serial = mock.MagicMock()
    mock_serial.in_waiting = 0
    mock_serial.read_until.side_effect = [b"not expected"]
    with pytest.raises(MicroBitIOError):
        microfs.raw_on(mock_serial)


def test_flush_to_msg_success() -> None:
    """Test that flush_to_msg does not raise when the expected message is received."""
    mock_serial = mock.MagicMock()
    msg = b"raw REPL; CTRL-B to exit\r\n>"
    mock_serial.read_until.return_value = msg
    microfs.flush_to_msg(mock_serial, msg)
    mock_serial.read_until.assert_called_once_with(msg)


def test_flush_to_msg_failure() -> None:
    """Test that flush_to_msg raises MicroBitIOError when the expected message is not received."""
    mock_serial = mock.MagicMock()
    msg = b"raw REPL; CTRL-B to exit\r\n>"
    mock_serial.read_until.return_value = b"something else"
    with pytest.raises(MicroBitIOError):
        microfs.flush_to_msg(mock_serial, msg)


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
    microfs.flush(mock_serial)
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
        mock.patch("microfs.find_microbit", return_value=mock_result),
        mock.patch("microfs.Serial", return_value=mock_serial),
    ):
        result = microfs.get_serial(10)
        assert result == mock_serial


def test_get_serial_no_port() -> None:
    """An MicroBitNotFoundError should be raised if no micro:bit is found."""
    with (
        mock.patch("microfs.find_microbit", return_value=(None, None)),
        pytest.raises(MicroBitNotFoundError) as ex,
    ):
        microfs.get_serial()
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
        mock.patch("microfs.get_serial", return_value=mock_serial),
        mock.patch("microfs.raw_on", return_value=None) as raw_mon,
        mock.patch("microfs.raw_off", return_value=None) as raw_moff,
    ):
        out = microfs.execute(commands, mock_serial)
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
        mock.patch("microfs.get_serial", return_value=mock_serial),
        mock.patch("microfs.raw_on", return_value=None),
        mock.patch("microfs.raw_off", return_value=None),
        mock.patch(
            "microfs.clean_error", return_value="errormsg"
        ) as mock_clean_error,
        pytest.raises(MicroBitIOError) as excinfo,
    ):
        microfs.execute(["cmd"], mock_serial)
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
        mock.patch("microfs.get_serial", return_value=mock_serial) as p,
        mock.patch("microfs.raw_on", return_value=None),
        mock.patch("microfs.raw_off", return_value=None),
    ):
        _ = microfs.execute(commands)
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
    result = microfs.clean_error(msg)
    assert result == "OSError: file not found"


def test_clean_error_no_stack_trace() -> None:
    """
    Sometimes stderr may not conform to the expected stacktrace structure. In
    which case, just return a string version of the message.
    """
    msg = b"This does not conform!"
    assert microfs.clean_error(msg) == "This does not conform!"


def test_clean_error_but_no_error() -> None:
    """
    Worst case, the function has been called with empty bytes so return a
    vague message.
    """
    assert microfs.clean_error(b"") == "There was an error."


def test_ls() -> None:
    """
    If a list is returned as a result in stdout, ensure that the equivalent
    Python list is returned from ls.
    """
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.execute", return_value=b"['a.txt']\r\n"
    ) as execute:
        result = microfs.ls(mock_serial)
        assert result == ["a.txt"]
        execute.assert_called_once_with(
            ["import os", "print(os.listdir())"], mock_serial, 10
        )


def test_ls_width_delimiter() -> None:
    """
    If a delimiter is provided, ensure that the result from stdout is
    equivalent to the list returned by Python.
    """
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.execute", return_value=(b"[ 'a.txt','b.txt']\r\n")
    ) as execute:
        result = microfs.ls(mock_serial)
        delimited_result = ";".join(result)
        assert delimited_result == "a.txt;b.txt"
        execute.assert_called_once_with(
            ["import os", "print(os.listdir())"], mock_serial, 10
        )


def test_rm() -> None:
    """Test that rm removes a file and returns True."""
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", return_value=b"") as execute:
        assert microfs.rm("foo", mock_serial)
        execute.assert_called_once_with(
            ["import os", "os.remove('foo')"], mock_serial, 10
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
        with mock.patch("microfs.execute", return_value=b"") as execute:
            assert microfs.put(file_path, "remote.txt", mock_serial)
            commands = [
                "fd = open('remote.txt', 'wb')",
                "f = fd.write",
                "f(b'hello')",
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial, 10)


def test_put_no_target() -> None:
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "fixture_file.txt"
        file_path.write_bytes(b"hello")
        mock_serial = mock.MagicMock()
        with mock.patch("microfs.execute", return_value=b"") as execute:
            assert microfs.put(file_path, None, mock_serial)
            commands = [
                f"fd = open('{file_path.name}', 'wb')",
                "f = fd.write",
                "f(b'hello')",
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial, 10)


def test_put_non_existent_file() -> None:
    """Test that put raises FileNotFoundError if the file does not exist."""
    with tempfile.NamedTemporaryFile() as tmp:
        file_path = pathlib.Path(tmp.name)
    mock_serial = mock.MagicMock()
    with pytest.raises(FileNotFoundError) as ex:
        microfs.put(file_path, mock_serial)
    assert ex.value.args[0] == "No such file."


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
                f"  u = UART(0, {SERIAL_BAUD_RATE})",
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
            mock.patch("microfs.execute", return_value=b"b'hello'") as exe,
            mock.patch.object(pathlib.Path, "open", mock.mock_open()) as mo,
        ):
            assert microfs.get("hello.txt", file_path, mock_serial)
            exe.assert_called_once_with(commands, mock_serial, 10)
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
            f"  u = UART(0, {SERIAL_BAUD_RATE})",
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
        mock.patch("microfs.execute", return_value=b"b'hello'") as exe,
        mock.patch.object(pathlib.Path, "open", mock.mock_open()) as mo,
    ):
        assert microfs.get("hello.txt")
        exe.assert_called_once_with(commands, None, 10)
        mo.assert_called_once_with("wb")
        handle = mo()
        handle.write.assert_called_once_with(b"hello")


def test_get_invalid_data() -> None:
    """Test that get raises MicroBitIOError if the returned data is not valid bytes."""
    mock_serial = mock.MagicMock()
    with (
        mock.patch("microfs.execute", return_value=b"notbytes"),
        pytest.raises(MicroBitIOError),
    ):
        microfs.get("foo.txt", pathlib.Path("bar.txt"), mock_serial)


def test_version_good_output() -> None:
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
    with mock.patch("microfs.execute", return_value=response) as execute:
        result = microfs.version(mock_serial)
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
            ["import os", "print(os.uname())"], mock_serial, 10
        )


def test_main_no_args() -> None:
    """If no args are passed, simply display help."""
    with mock.patch("sys.argv", ["ufs"]):
        mock_parser = mock.MagicMock()
        with mock.patch(
            "microfs.argparse.ArgumentParser", return_value=mock_parser
        ):
            microfs.main()
        mock_parser.print_help.assert_called_once_with()


def test_main_ls() -> None:
    """If the ls command is issued, check the appropriate function is called."""
    with (
        mock.patch("microfs.ls", return_value=["foo", "bar"]) as mock_ls,
        mock.patch("microfs.logger.info") as mock_logger_info,
    ):
        microfs.main(argv=["ls"])
        mock_ls.assert_called_once_with(timeout=10)
        mock_logger_info.assert_called_once_with("Found files: %s", "foo bar")


def test_main_ls_with_timeout() -> None:
    """If the ls command is issued, check the appropriate function is called."""
    with (
        mock.patch("microfs.ls", return_value=["foo", "bar"]) as mock_ls,
        mock.patch("microfs.logger.info") as mock_logger_info,
    ):
        microfs.main(argv=["ls", "-t", "3"])
        mock_ls.assert_called_once_with(timeout=3)
        mock_logger_info.assert_called_once_with("Found files: %s", "foo bar")


def test_main_ls_no_files() -> None:
    """If the ls command is issued and no files exist, nothing is printed."""
    with (
        mock.patch("microfs.ls", return_value=[]) as mock_ls,
        mock.patch("microfs.logger.info") as mock_logger_info,
    ):
        microfs.main(argv=["ls"])
        mock_ls.assert_called_once_with(timeout=10)
        mock_logger_info.assert_not_called()


def test_main_rm() -> None:
    """
    If the rm command is correctly issued, check the appropriate function is
    called.
    """
    with mock.patch("microfs.rm", return_value=True) as mock_rm:
        microfs.main(argv=["rm", "foo"])
        mock_rm.assert_called_once_with(filename="foo", timeout=10)


def test_main_rm_with_timeout() -> None:
    """
    If the rm command is correctly issued, check the appropriate function is
    called.
    """
    with mock.patch("microfs.rm", return_value=True) as mock_rm:
        microfs.main(argv=["rm", "foo", "-t", "3"])
        mock_rm.assert_called_once_with(filename="foo", timeout=3)


def test_main_rm_no_filename() -> None:
    """
    If rm is not called with an associated filename, then print an error
    message.
    """
    with (
        mock.patch("microfs.logger.error") as mock_logger_error,
        pytest.raises(SystemExit) as pytest_exc,
    ):
        microfs.main(argv=["rm"])
    mock_logger_error.assert_called_once_with(
        'rm: error: missing filename. (e.g. "ufs rm foo.txt")'
    )
    assert pytest_exc.type is SystemExit
    assert pytest_exc.value.code == 2


def test_main_put() -> None:
    """
    If the put command is correctly issued, check the appropriate function is
    called.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "foo.txt"
        file_path.write_text("abc")
        with mock.patch("microfs.put", return_value=True) as mock_put:
            microfs.main(argv=["put", str(file_path)])
            mock_put.assert_called_once_with(
                filename=file_path, target=None, timeout=10
            )


def test_main_put_with_timeout() -> None:
    """
    If the put command is correctly issued, check the appropriate function is
    called.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = pathlib.Path(tmpdir) / "foo.txt"
        file_path.write_text("abc")
        with mock.patch("microfs.put", return_value=True) as mock_put:
            microfs.main(argv=["put", str(file_path), "-t", "3"])
            mock_put.assert_called_once_with(
                filename=file_path, target=None, timeout=3
            )


def test_main_put_no_filename() -> None:
    """
    If put is not called with an associated filename, then print an error
    message.
    """
    with (
        mock.patch("microfs.logger.error") as mock_logger_error,
        pytest.raises(SystemExit) as pytest_exc,
    ):
        microfs.main(argv=["put"])
    mock_logger_error.assert_called_once_with(
        'put: error: missing filename. (e.g. "ufs put foo.txt")'
    )
    assert pytest_exc.type is SystemExit
    assert pytest_exc.value.code == 2


def test_main_get() -> None:
    """
    If the get command is correctly issued, check the appropriate function is
    called.
    """
    with mock.patch("microfs.get", return_value=True) as mock_get:
        microfs.main(argv=["get", "foo"])
        mock_get.assert_called_once_with(
            filename="foo", target=None, timeout=10
        )


def test_main_get_with_timeout() -> None:
    """
    If the get command is correctly issued, check the appropriate function is
    called.
    """
    with mock.patch("microfs.get", return_value=True) as mock_get:
        microfs.main(argv=["get", "foo", "-t", "3"])
        mock_get.assert_called_once_with(
            filename="foo", target=None, timeout=3
        )


def test_main_get_no_filename() -> None:
    """
    If get is not called with an associated filename, then print an error
    message.
    """
    with (
        mock.patch("microfs.logger.error") as mock_logger_error,
        pytest.raises(SystemExit) as pytest_exc,
    ):
        microfs.main(argv=["get"])
    mock_logger_error.assert_called_once_with(
        'get: error: missing filename. (e.g. "ufs get foo.txt")'
    )
    assert pytest_exc.type is SystemExit
    assert pytest_exc.value.code == 2


def test_main_version() -> None:
    """Test that main prints version information when 'version' command is used."""
    version_info = {"sysname": "microbit", "release": "1.0"}
    with (
        mock.patch(
            "microfs.version", return_value=version_info
        ) as mock_version,
        mock.patch("microfs.logger.info") as mock_logger_info,
    ):
        microfs.main(argv=["version"])
        mock_version.assert_called_once_with(timeout=10)
        mock_logger_info.assert_any_call("%s: %s", "sysname", "microbit")
        mock_logger_info.assert_any_call("%s: %s", "release", "1.0")


def test_main_handle_exception() -> None:
    """If an exception is raised, then it gets printed."""
    ex = MicroBitIOError("Error")
    with (
        mock.patch("microfs.get", side_effect=ex),
        mock.patch("microfs.logger.exception") as mock_logger_exception,
        pytest.raises(SystemExit) as pytest_exc,
    ):
        microfs.main(argv=["get", "foo"])
    mock_logger_exception.assert_called_once_with(
        "An error occurred during execution:"
    )
    assert pytest_exc.type is SystemExit
    assert pytest_exc.value.code == 1


def test_main_version_flag() -> None:
    """Test that main prints version when '--version' flag is used."""
    with mock.patch(
        "microfs.importlib.metadata.version", return_value=MICROFS_VERSION
    ):
        with (
            mock.patch("sys.stdout") as mock_stdout,
            pytest.raises(SystemExit) as pytest_exc,
        ):
            microfs.main(argv=["--version"])
        output = "".join(
            call.args[0] for call in mock_stdout.write.call_args_list
        )
        assert f"microfs version: {MICROFS_VERSION}" in output
        assert pytest_exc.type is SystemExit


def test_main_uses_sys_argv_when_none() -> None:
    """Test that main uses sys.argv[1:] if argv is None."""
    with (
        mock.patch("sys.argv", ["progname", "ls"]),
        mock.patch("microfs.ls", return_value=["foo"]) as mock_ls,
        mock.patch("microfs.logger.info") as mock_logger_info,
    ):
        microfs.main(argv=None)
        mock_ls.assert_called_once_with(timeout=10)
        mock_logger_info.assert_called_once_with("Found files: %s", "foo")
