from ._base import Provider


class ZhipuAIProvider(Provider):
    __mapper_args__ = {"polymorphic_identity": "ZHIPUAI_SDK"}

    def get_client(self):
        from mc_bench.clients.zhipuai import ZhipuAIClient

        return ZhipuAIClient()
