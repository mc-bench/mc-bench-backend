from mc_bench.clients.openai import OpenAIClient

from ._base import Provider


class DeepSeekProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "DEEPSEEK_SDK"}

    def get_client(self):
        return OpenAIClient()
