# Copyright (c) 2025 Blackteahamburger <blackteahamburger@outlook.com>
#
# See the LICENSE file for more information.
from collections.abc import Callable as Callable

from microfs.lib import MicroBitIOError as MicroBitIOError
from microfs.lib import MicroBitNotFoundError as MicroBitNotFoundError
from microfs.lib import MicroBitSerial as MicroBitSerial
from microfs.lib import cat as cat
from microfs.lib import cp as cp
from microfs.lib import du as du
from microfs.lib import get as get
from microfs.lib import ls as ls
from microfs.lib import micropython_version as micropython_version
from microfs.lib import mv as mv
from microfs.lib import put as put
from microfs.lib import rm as rm
from microfs.lib import version as version

def main() -> None: ...
