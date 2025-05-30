import abc


class AbstractTextureCache(abc.ABC):
    @abc.abstractmethod
    def get_texture(self, name: str):
        pass

    @abc.abstractmethod
    def put_texture(self, name: str, image_data: bytes):
        pass
