from mc_bench.clients.gemini import GeminiClient

from ._base import Provider


class GeminiProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "GEMINI_SDK"}

    def get_client(self):
        return GeminiClient()
