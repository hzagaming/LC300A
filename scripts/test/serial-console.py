#!/usr/bin/env python3

import argparse
import os
import select
import socket
import time
from pathlib import Path


def connect(path: Path, timeout: int = 30) -> socket.socket:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.connect(str(path))
            connection.setblocking(False)
            return connection
        except OSError:
            connection.close()
            time.sleep(0.1)
    raise TimeoutError(f"无法连接 QEMU 串口: {path}")


def bridge(socket_path: Path, log_path: Path, command_pipe: Path) -> None:
    connection = connect(socket_path)
    command_fd = os.open(command_pipe, os.O_RDWR | os.O_NONBLOCK)
    try:
        with log_path.open("ab", buffering=0) as log:
            while True:
                readable, _, _ = select.select((connection, command_fd), (), (), 1)
                if connection in readable:
                    data = connection.recv(65536)
                    if not data:
                        return
                    log.write(data)
                if command_fd in readable:
                    data = os.read(command_fd, 65536)
                    if data:
                        connection.sendall(data)
    finally:
        os.close(command_fd)
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge a QEMU serial socket to a log and command pipe")
    parser.add_argument("socket", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("command_pipe", type=Path)
    arguments = parser.parse_args()
    bridge(arguments.socket, arguments.log, arguments.command_pipe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
