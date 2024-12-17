import requests

from mc_bench.auth.emails import hash_email
from mc_bench.apps.api.config import settings


class GithubOauthClient:
    def __init__(self, client_id: str, client_secret: str, salt: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.salt = salt

    def get_user_id(self, access_token):
        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        return user_response.json()["id"]

    def get_user_email_hashes(self, access_token):
        email_response = requests.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        email_response.raise_for_status()
        user_email_data = email_response.json()
        user_email_hashes = [
            hash_email(email["email"], self.salt)
            for email in user_email_data
            if email["verified"]
        ]

        return user_email_hashes

    def get_access_token(self, code: str):
        # Exchange code for access token
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_response.raise_for_status()
        return token_response.json()["access_token"]

    def get_github_info(self, access_token):
        user_id = self.get_user_id(access_token)
        user_email_hashes = self.get_user_email_hashes(access_token)
        return {"user_id": str(user_id), "user_email_hashes": user_email_hashes}
    

class XOauthClient:
    def __init__(self, client_id: str, client_secret: str, salt: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.salt = salt
        self.redirect_uri = redirect_uri

    def get_access_token(self, code: str) -> str:
        # Exchange code for access token
        token_response = requests.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_response.raise_for_status()
        return token_response.json()["access_token"]

    def get_user_id(self, access_token: str) -> str:
        user_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )
        user_response.raise_for_status()
        return user_response.json()["data"]["id"]

    def get_user_email_hashes(self, access_token: str) -> list:
        email_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            params={"user.fields": "email"},
        )
        email_response.raise_for_status()
        email = email_response.json()["data"].get("email")
        return [hash_email(email, self.salt)] if email else []

    def get_x_info(self, access_token: str) -> dict:
        user_id = self.get_user_id(access_token)
        user_email_hashes = self.get_user_email_hashes(access_token)
        return {"user_id": str(user_id), "user_email_hashes": user_email_hashes}


# Instantiate the X client (similar to GitHub instantiation)
x_oauth_client = XOauthClient(
    client_id=settings.X_CLIENT_ID,
    client_secret=settings.X_CLIENT_SECRET,
    salt=settings.OAUTH_SALT,
    redirect_uri=settings.REDIRECT_URI
)







