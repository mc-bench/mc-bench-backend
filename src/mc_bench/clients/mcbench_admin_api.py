import os

import requests

from dotenv import load_dotenv

load_dotenv()


class Client:
    def __init__(self, token):
        self.token = token
        self.base_url = os.environ["ADMIN_API_URL"]

    def _make_path(self, path):
        path = path.lstrip("/")
        host = self.base_url.rstrip("/")
        return f"{host}/{path}"

    def _make_request(self, method, path, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"}

        return requests.request(
            method, self._make_path(path), headers=headers, **kwargs
        )

    def post(self, path, **kwargs):
        return self._make_request("POST", path, **kwargs)

    def update_stage_progress(self, run_external_id, stage, progress, note):
        response = self.post(
            f"/api/run/{run_external_id}/task/progress",
            json={
                "stage": stage,
                "progress": progress,
                "note": note,
            },
        )
        response.raise_for_status()
