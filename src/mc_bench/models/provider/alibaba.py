from ._base import Provider


class AlibabaProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "ALIBABA_SDK"}

    def get_client(self):
        from mc_bench.clients.alibaba_cloud import AlibabaCloudClient

        return AlibabaCloudClient()
