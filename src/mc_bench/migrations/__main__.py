import sys

from alembic.config import CommandLine, Config


def get_alembic_config():
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "mc_bench:migrations")

    return alembic_cfg


def main():
    cli = CommandLine(prog=sys.argv[0])

    options = cli.parser.parse_args()
    if not hasattr(options, "cmd"):
        cli.parser.error("too few arguments")

    cmd, args_keys, kwargs_keys = options.cmd
    alembic_cfg = get_alembic_config()
    alembic_cfg.cmd_opts = options
    cmd(
        alembic_cfg,
        *[getattr(options, k, None) for k in args_keys],
        **dict((k, getattr(options, k, None)) for k in kwargs_keys),
    )
