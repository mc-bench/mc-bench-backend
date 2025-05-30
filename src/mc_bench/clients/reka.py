import os

from reka.client import Reka


class RekaClient:
    def __init__(self):
        self.client = Reka(api_key=os.environ["REKA_API_KEY"])

    def send_prompt(self, **kwargs):
        prompt_in_kwargs = "prompt" in kwargs
        messages_in_kwargs = "messages" in kwargs
        assert not (messages_in_kwargs and prompt_in_kwargs)
        assert messages_in_kwargs or prompt_in_kwargs
        assert "model" in kwargs

        if prompt_in_kwargs:
            kwargs["messages"] = [
                {
                    "role": "user",
                    "content": kwargs.pop("prompt"),
                }
            ]
        try:
            response = self.client.chat.create(**kwargs)
            return response.responses[0].message.content
        except Exception as e:
            raise Exception(f"Error calling Reka API: {str(e)}")
