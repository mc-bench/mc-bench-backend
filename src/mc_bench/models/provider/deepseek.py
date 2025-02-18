from ._base import Provider


class DeepSeekProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "DEEPSEEK_SDK"}

    def get_client(self):
        from mc_bench.clients.deepseek import DeepSeekClient

        return DeepSeekClient()
