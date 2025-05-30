import abc
from typing import List


class AuthenticationClient(abc.ABC):
    @abc.abstractmethod
    def get_username(self, **kwargs) -> str:
        pass

    @abc.abstractmethod
    def get_user_id(self, **kwargs) -> str:
        pass

    @abc.abstractmethod
    def get_user_emails(self, **kwargs) -> List[str]:
        pass

    @abc.abstractmethod
    def get_access_token(self, **kwargs) -> str:
        pass
