from mc_bench.clients.openrouter import OpenRouterClient

from ._base import Provider


class OpenRouterProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "OPENROUTER_SDK"}

    def get_client(self):
        return OpenRouterClient()
