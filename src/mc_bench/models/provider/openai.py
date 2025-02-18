from ._base import Provider


class OpenAIProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "OPENAI_SDK"}

    def get_client(self):
        from mc_bench.clients.openai import OpenAIClient

        return OpenAIClient()
