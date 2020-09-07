"""A wrapper around ssh and sshfs for easy remote environment setup."""

import pathlib
import subprocess  # nosec
import warnings

from typing import Iterable

import click
import toml
import xdg

from neurax import APP_NAME


CONFIG_ROOT = xdg.XDG_CONFIG_HOME / APP_NAME
CONFIGS_DIR = CONFIG_ROOT / "configs"


def socket_path(host_name: str) -> pathlib.Path:
    runtime_dir = xdg.XDG_RUNTIME_DIR
    if runtime_dir is None:
        warnings.warn("XDG_RUNTIME_DIR undefined, falling back to your home")
        runtime_dir = xdg.XDG_DATA_HOME
    return runtime_dir / APP_NAME / "sockets" / host_name


def send_control_command(host_name: str, command: str) -> int:
    socket = str(socket_path(host_name))
    result = subprocess.run((["ssh", "-S", socket, "-O", command, host_name]))
    return result.returncode


def is_alive(host_name: str) -> bool:
    if not socket_path(host_name).exists():
        return False
    return send_control_command(host_name, "check") == 0


def open_shell(host_name: str):
    socket = socket_path(host_name)
    subprocess.run(["ssh", "-S", str(socket), host_name])


def mount_remote(host_name: str, remote_path: str, mount_point: pathlib.Path):
    mount_point.mkdir(exist_ok=True, parents=True)
    subprocess.run(
        [
            "sshfs",
            "-o",
            f"ssh_command=ssh -S {socket_path(host_name)}",
            f"{host_name}:{remote_path}",
            str(mount_point),
        ],
        check=True,
    )


def unmount(mount_point: pathlib.Path):
    subprocess.run(["fusermount", "-u", str(mount_point)])


def disconnect(host_name: str):
    send_control_command(host_name, "exit")


def connect(host_name: str, ssh_opts: Iterable[str]):
    socket = socket_path(host_name)
    socket.parent.mkdir(exist_ok=True, parents=True)
    subprocess.run(
        ["ssh", "-f", "-N", "-M", "-S", str(socket), *ssh_opts, host_name], check=True
    )


@click.group()
def cli():
    pass


@cli.command("list", help="List available named configs")
def list_configs():
    for config_file in CONFIGS_DIR.glob("*.toml"):
        print(config_file.stem)


@cli.command("connect", help="Connect to a remote using an existing config")
@click.argument(
    "config_name_or_path",
    type=str,
)
def connect_cli(config_name_or_path: str):
    config_path = pathlib.Path(config_name_or_path)
    if not config_path.exists():
        config_path = CONFIGS_DIR / f"{config_name_or_path}.toml"
        if not config_path.exists():
            click.echo(
                f"{config_name_or_path} is neither the path to a valid config or the name of a saved config"
            )
            click.Context.exit(1)
    config = toml.loads(config_path.read_text())

    host_name = config["host"]

    if not is_alive(host_name):
        connect(host_name, config.get("ssh_opts", []))
        if config.get("dirs"):
            mount_root = pathlib.Path(config["mount_root"])
            for dir_local_name, dir_config in config["dirs"].items():
                local_mount_point = mount_root / dir_local_name
                remote_path = dir_config["remote_path"]
                mount_remote(host_name, remote_path, local_mount_point)

    open_shell(host_name)


@cli.command("disconnect", help="Disconnect from a remote and unmount its dirs")
@click.argument(
    "config_name_or_path",
    type=str,
)
def disconnect_cli(config_name_or_path: str):
    config_path = pathlib.Path(config_name_or_path)
    if not config_path.exists():
        config_path = CONFIGS_DIR / f"{config_name_or_path}.toml"
        if not config_path.exists():
            click.echo(
                f"{config_name_or_path} is neither the path to a valid config or the name of a saved config"
            )
            click.Context.exit(1)
    config = toml.loads(config_path.read_text())

    host_name = config["host"]

    if config.get("dirs"):
        mount_root = pathlib.Path(config["mount_root"])
        for dir_local_name, dir_config in config["dirs"].items():
            local_mount_point = mount_root / dir_local_name
            unmount(local_mount_point)

    disconnect(host_name)


@cli.command(
    "socket",
    help="Print the path to a control socket for a given remote, initiating connection if needed",
)
@click.argument(
    "config_name_or_path",
    type=str,
)
def socket_cli(config_name_or_path: str):
    config_path = pathlib.Path(config_name_or_path)
    if not config_path.exists():
        config_path = CONFIGS_DIR / f"{config_name_or_path}.toml"
        if not config_path.exists():
            click.echo(
                f"{config_name_or_path} is neither the path to a valid config or the name of a saved config"
            )
            click.Context.exit(1)
    config = toml.loads(config_path.read_text())

    host_name = config["host"]

    if not is_alive(host_name):
        connect(host_name, config.get("ssh_opts", []))

    print(socket_path(host_name))
