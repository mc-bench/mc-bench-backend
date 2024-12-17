import requests
import base64

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
    def __init__(self, client_id: str, client_secret: str, salt: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.salt = salt

    def get_access_token(self, code: str) -> str:
        # Create Basic Auth header by combining client_id:client_secret and encoding to base64
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')
        
        # Exchange code for access token
        token_response = requests.post(
            "https://api.x.com/2/oauth2/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {base64_auth}",
            },
            data={
                "code": code,
                "grant_type" :"authorization_code",
                "client_id": self.client_id,
                "redirect_uri": settings.REDIRECT_URI,
                "code_verifier": "challenge"
            }
        )
        
        # Keep debug logging
        print(f"Token response status code: {token_response.status_code}")
        print(f"Token response headers: {token_response.headers}")
        print(f"Token response body: {token_response.text}")
        
        token_response.raise_for_status()
        return token_response.json()["access_token"]

    def get_user_id(self, access_token: str) -> str:
        user_response = requests.get(
            "https://api.x.com/2/users/me",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )
        user_response.raise_for_status()
        return user_response.json()["data"]["id"]

    def get_user_email_hashes(self, access_token: str) -> list:
        email_response = requests.get(
            "https://api.x.com/2/users/me",
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







