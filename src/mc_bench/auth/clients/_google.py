import requests
from typing import List

from ._base import AuthenticationClient


class GoogleOauthClient(AuthenticationClient):
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"

    def get_access_token(self, code: str) -> str:
        # Exchange code for access token
        token_response = requests.post(
            self.token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        token_response.raise_for_status()
        return token_response.json()["access_token"]

    def get_user_id(self, access_token: str) -> str:
        user_info = self._get_user_info(access_token)
        return user_info["sub"]

    def get_username(self, access_token: str) -> str:
        user_info = self._get_user_info(access_token)
        return user_info.get("name", user_info["email"])

    def get_user_emails(self, access_token: str) -> List[str]:
        user_info = self._get_user_info(access_token)
        return [user_info["email"]]

    def _get_user_info(self, access_token: str) -> dict:
        user_response = requests.get(
            self.userinfo_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        user_response.raise_for_status()
        return user_response.json()