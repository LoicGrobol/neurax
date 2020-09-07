Neurax
======

An ssh/sshfs wrapper to improve your mind control over remote machines.

- Establishes an [ssh multiplexed
  connection](https://en.wikibooks.org/wiki/OpenSSH/Cookbook/Multiplexing)
- Uses it to mount remote directories of your choice in local path of your choices so you can access
  them as if there were on your machine
- Open as many shells as you want
- And more! Coming soon! I swear! Hopefully!

## Installation

You will need `ssh` (OpenSSH >3.9 works, I have not tested anything else yet) and `sshfs` installed
and in your path to use Neurax, install them anyway you want. Then install Neurax. Vanilla pip
should work but I recommend [pipx](https://pipxproject.github.io/pipx/)

```console
pipx install neurax
```

## Usage

1. Create a config file (in [TOML](https://toml.io)) for the host you want to connect to, see
   examples in [`examples/`](examples/)
2. (optional) if you want to be able to use this config by name, add it as
   `~/.config/neurax/configs/some_name.toml` (or the equivalent [XDG Base
   directory](https://specifications.freedesktop.org/basedir-spec/latest/) on your machine)
3. Connect by running `neurax connect path/to/your/config.toml` or `neurax connect some_names` if
   you followed step 2. Running this several times will open new shells through the same multiplexed
   connection, which will not close even if you exit the shell (so your mounts stay up)
4. Disconnect by running `neurax --config path/to/your/config/file disconnect`. This closes the
   multiplexed connection.
