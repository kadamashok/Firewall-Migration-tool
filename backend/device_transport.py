from __future__ import annotations

import socket
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

import paramiko

try:
    from netmiko import ConnectHandler
except Exception:  # pragma: no cover
    ConnectHandler = None


class DeviceConnectionError(Exception):
    pass


class DeviceAuthenticationError(Exception):
    pass


@dataclass
class DeviceCredentials:
    ip: str
    username: str
    password: str
    ssh_port: int = 22


def ping_tcp(ip: str, port: int = 22, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


class SSHTransport(AbstractContextManager):
    def __init__(self, creds: DeviceCredentials):
        self.creds = creds
        self._netmiko_conn = None
        self._paramiko = None

    def connect(self) -> None:
        if ConnectHandler:
            try:
                self._netmiko_conn = ConnectHandler(
                    device_type="autodetect",
                    host=self.creds.ip,
                    username=self.creds.username,
                    password=self.creds.password,
                    port=self.creds.ssh_port,
                    timeout=15,
                )
                return
            except Exception:
                self._netmiko_conn = None
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=self.creds.ip,
                username=self.creds.username,
                password=self.creds.password,
                port=self.creds.ssh_port,
                look_for_keys=False,
                allow_agent=False,
                timeout=15,
            )
            self._paramiko = client
        except paramiko.AuthenticationException as exc:
            raise DeviceAuthenticationError("Authentication failed") from exc
        except Exception as exc:
            raise DeviceConnectionError(str(exc)) from exc

    def run_command(self, command: str) -> str:
        if self._netmiko_conn:
            return str(self._netmiko_conn.send_command(command, read_timeout=30))
        if self._paramiko:
            stdin, stdout, stderr = self._paramiko.exec_command(command, timeout=30)
            _ = stdin
            out = stdout.read().decode(errors="ignore")
            err = stderr.read().decode(errors="ignore")
            return out or err
        raise DeviceConnectionError("SSH transport not connected")

    def push_commands(self, commands: list[str]) -> str:
        if not commands:
            return "No commands to push"
        if self._netmiko_conn:
            return str(self._netmiko_conn.send_config_set(commands))
        if self._paramiko:
            shell = self._paramiko.invoke_shell()
            for cmd in commands:
                shell.send(cmd + "\n")
            return "Commands sent via interactive shell"
        raise DeviceConnectionError("SSH transport not connected")

    def close(self) -> None:
        if self._netmiko_conn:
            self._netmiko_conn.disconnect()
            self._netmiko_conn = None
        if self._paramiko:
            self._paramiko.close()
            self._paramiko = None

    def __enter__(self) -> "SSHTransport":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
