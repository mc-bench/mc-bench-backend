from ._base import Provider


class AnthropicProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "ANTHROPIC_SDK"}

    def get_client(self):
        from mc_bench.clients.anthropic import AnthropicClient

        return AnthropicClient()
