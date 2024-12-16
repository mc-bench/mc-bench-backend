import re


def parse_known_parts(text):
    tags = ["code", "inspiration", "description"]
    result = {}

    # Parse each tag
    for tag in tags:
        pattern = f"<{tag}>(.*?)</{tag}>"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches and matches[0]:
            result[tag] = matches[0]

    if not result.get("inspiration"):
        try:
            start_index = text.index("<inspiration>") + len("<inspiration>")
            end_index = text.index("<description>")
            result["inspiration"] = text[start_index:end_index].strip()
        except ValueError:
            pass

    if not result.get("description"):
        try:
            start_index = text.index("<description>") + len("<description>")
            end_index = text.index("<code>")
            result["description"] = text[start_index:end_index].strip()
        except ValueError:
            pass

    if not result.get("code"):
        for parse_func in [
            try_parse_code_from_start_tag,
            try_parse_code_from_hash_tick_block,
        ]:
            code = parse_func(text)
            if code:
                result["code"] = code
                break

    return result


def try_parse_code_from_start_tag(text):
    try:
        start_index = text.index("<code>") + len("<code>")
        return text[start_index:].strip()
    except ValueError:
        return None


def try_parse_code_from_hash_tick_block(text):
    try:
        start_index = text.find("```javascript") + len("```javascript")

        end_index = start_index + 1
        while True:
            end_index = text.find("```", end_index)

            if end_index > start_index:
                break

            if end_index == -1:
                print("No end of code block found")
                raise ValueError("No end of code block found")

        return text[start_index:end_index].strip()
    except ValueError:
        return None
