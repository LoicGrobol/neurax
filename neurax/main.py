"""A wrapper around ssh and sshfs for easy remote environment setup."""

import pathlib
import subprocess  # nosec
import warnings

from typing import Iterable, Optional

import click
import click_pathlib
import toml
import xdg

from neurax import APP_NAME


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
            f'ssh_command=ssh -S {socket_path(host_name)}',
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
@click.option(
    "--name",
    "config_name",
    type=str,
    help="The name of a known config",
)
@click.option(
    "--config",
    "config_path",
    type=click_pathlib.Path(resolve_path=True, dir_okay=False, exists=True),
    help="A config file (in TOML format)",
)
@click.pass_context
def cli(
    ctx: click.Context, config_name: Optional[str], config_path: Optional[pathlib.Path]
):
    if config_path is not None:
        config = toml.loads(config_path.read_text())
    elif config_name is not None:
        config_path = xdg.XDG_CONFIG_HOME / APP_NAME / "configs" / f"{config_name}.toml"
        if not config_path.exists():
            raise ValueError(f"No config for {config_name} in {config_path.parent}")
        config = toml.loads(config_path.read_text())
    else:
        raise ValueError("Either --config or --name must be specified")

    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@cli.command("connect")
@click.pass_context
def connect_cli(ctx: click.Context):
    config = ctx.obj["config"]
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


@cli.command("disconnect")
@click.pass_context
def disconnect_cli(ctx: click.Context):
    config = ctx.obj["config"]
    host_name = config["host"]

    if config.get("dirs"):
        mount_root = pathlib.Path(config["mount_root"])
        for dir_local_name, dir_config in config["dirs"].items():
            local_mount_point = mount_root / dir_local_name
            unmount(local_mount_point)

    disconnect(host_name)