from ._base import Provider


class OpenAIResponsesProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "OPENAI_RESPONSES_SDK"}

    def get_client(self):
        from mc_bench.clients.openai_responses import OpenAIResponsesClient

        return OpenAIResponsesClient()
