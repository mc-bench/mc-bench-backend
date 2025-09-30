import os

import openai


class OpenAIResponsesClient:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def send_prompt(self, **kwargs):
        prompt_in_kwargs = "prompt" in kwargs
        messages_in_kwargs = "messages" in kwargs
        input_in_kwargs = "input" in kwargs

        assert not (messages_in_kwargs and prompt_in_kwargs)
        assert not (input_in_kwargs and (messages_in_kwargs or prompt_in_kwargs))
        assert messages_in_kwargs or prompt_in_kwargs or input_in_kwargs
        assert "model" in kwargs

        # Convert prompt to input format for Responses API
        if prompt_in_kwargs:
            kwargs["input"] = kwargs.pop("prompt")
        elif messages_in_kwargs:
            # Convert messages format to input format
            messages = kwargs.pop("messages")
            if len(messages) == 1 and messages[0]["role"] == "user":
                kwargs["input"] = messages[0]["content"]
            else:
                # For multi-turn conversations, use the messages format as input
                kwargs["input"] = messages

        # Use the OpenAI Responses API
        response = self.client.responses.create(**kwargs)
        return response.output_text
