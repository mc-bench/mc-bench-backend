import os

import openai


class OpenRouterClient:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )

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

        chat_completion = self.client.chat.completions.create(**kwargs)
        return chat_completion.choices[0].message.content
