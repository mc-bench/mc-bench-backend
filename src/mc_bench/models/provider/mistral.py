from ._base import Provider


class MistralProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "MISTRAL_SDK"}

    def get_client(self):
        from mc_bench.clients.mistral import MistralClient

        return MistralClient()
