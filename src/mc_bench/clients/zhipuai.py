import os

import openai


class ZhipuAIClient:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.environ["ZHIPUAI_API_KEY"],
            base_url="https://open.bigmodel.cn/api/paas/v4/",
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
            raise Exception(f"Error calling ZhipuaAI API: {str(e)}")
