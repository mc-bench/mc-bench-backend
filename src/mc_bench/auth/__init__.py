import requests

from mc_bench.auth.emails import hash_email


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
