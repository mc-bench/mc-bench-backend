from ._base import Provider


class RekaProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "REKA_SDK"}

    def get_client(self):
        from mc_bench.clients.reka import RekaClient

        return RekaClient()
