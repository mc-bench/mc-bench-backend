from mc_bench.clients.anthropic import AnthropicClient

from ._base import Provider


class AnthropicProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "ANTHROPIC_SDK"}

    def get_client(self):
        return AnthropicClient()
