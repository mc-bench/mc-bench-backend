import os

from openai import OpenAI


class GrokClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1"
        )

    def send_prompt(self, **kwargs):
        prompt_in_kwargs = "prompt" in kwargs
        messages_in_kwargs = "messages" in kwargs
        assert not (messages_in_kwargs and prompt_in_kwargs)
        assert messages_in_kwargs or prompt_in_kwargs
        assert "model" in kwargs

        # Convert single prompt to messages if needed
        if prompt_in_kwargs:
            kwargs["messages"] = [
                {
                    "role": "user",
                    "content": kwargs.pop("prompt"),
                }
            ]

        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error in Grok API call: {str(e)}")
