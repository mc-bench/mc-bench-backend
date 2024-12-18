import requests

from mc_bench.auth.emails import hash_email

from ._base import AuthenticationClient


class GithubOauthClient(AuthenticationClient):
    def __init__(self, client_id: str, client_secret: str, salt: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.salt = salt

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

    def get_user_id(self, access_token):
        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        user_response.raise_for_status()
        return user_response.json()["id"]

    def get_username(self, access_token):
        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        user_response.raise_for_status()
        return user_response.json()["login"]

    def get_user_emails(self, access_token):
        email_response = requests.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        email_response.raise_for_status()
        return [email["email"] for email in email_response.json() if email["verified"]]

    def get_user_email_hashes(self, access_token):
        emails = self.get_user_emails(access_token)
        return [hash_email(email, self.salt) for email in emails]

    def get_github_info(self, access_token):
        user_id = self.get_user_id(access_token)
        user_email_hashes = self.get_user_email_hashes(access_token)
        return {"user_id": str(user_id), "user_email_hashes": user_email_hashes}
