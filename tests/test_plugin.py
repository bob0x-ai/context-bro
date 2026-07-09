from context_bro.plugin import register
import argparse


class FakeCtx:
    def __init__(self) -> None:
        self.cli = None
        self.slash = None

    def register_cli_command(self, **kwargs):
        self.cli = kwargs

    def register_command(self, *args, **kwargs):
        self.slash = (args, kwargs)


def test_register_exposes_cli_and_slash_commands() -> None:
    ctx = FakeCtx()
    register(ctx)
    assert ctx.cli["name"] == "context-inspect"
    assert ctx.slash[0] == ("context",)


def test_cli_setup_works_with_builtin_argparse_help() -> None:
    ctx = FakeCtx()
    register(ctx)
    parser = argparse.ArgumentParser(prog="hermes")
    subparsers = parser.add_subparsers(dest="command")
    plugin_parser = subparsers.add_parser(ctx.cli["name"])

    ctx.cli["setup_fn"](plugin_parser)
    if ctx.cli["handler_fn"] is not None:
        plugin_parser.set_defaults(func=ctx.cli["handler_fn"])

    args = parser.parse_args(["context-inspect"])

    assert args.command == "context-inspect"
    assert callable(args.func)
