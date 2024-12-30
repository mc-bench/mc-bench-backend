from mc_bench.clients.grok import GrokClient

from ._base import Provider


class GrokProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "GROK_SDK"}

    def get_client(self):
        return GrokClient()
