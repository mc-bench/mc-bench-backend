import os

import openai


class AlibabaCloudClient:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.environ["ALIBABA_CLOUD_API_KEY"],
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
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
        try:
            chat_completion = self.client.chat.completions.create(**kwargs)
            return chat_completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error calling Alibaba Cloud API: {str(e)}")
