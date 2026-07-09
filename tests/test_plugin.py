from context_bro.plugin import register


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

