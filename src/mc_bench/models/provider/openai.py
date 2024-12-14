from mc_bench.clients.openai import OpenAIClient

from ._base import Provider


class OpenAIProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "OPENAI_SDK"}

    def get_client(self):
        return OpenAIClient()
