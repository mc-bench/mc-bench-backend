import textwrap

from mc_bench.util.text import (
    parse_known_parts,
    try_parse_code_from_hash_tick_block,
    try_parse_code_from_start_tag,
)


def test_parse_known_parts_with_tags():
    input_text = """
    <inspiration>This is the inspiration</inspiration>
    <description>This is the description</description>
    <code>console.log('Hello');</code>
    """
    result = parse_known_parts(input_text)

    assert result["inspiration"] == "This is the inspiration"
    assert result["description"] == "This is the description"
    assert result["code"] == "console.log('Hello');"


def test_parse_known_parts_with_markdown_code():
    input_text = textwrap.dedent("""\
    <inspiration>This is the inspiration</inspiration>
    <description>This is the description</description>    ```javascript
    console.log('Hello');
    const x = 42;    ```
    """)
    result = parse_known_parts(input_text)

    assert result["inspiration"] == "This is the inspiration"
    assert result["description"] == "This is the description"
    assert result["code"] == "console.log('Hello');\nconst x = 42;"


def test_parse_known_parts_with_missing_tags():
    input_text = """
    <inspiration>This is the inspiration
    <description>This is the description
    <code>console.log('Hello');</code>
    """
    result = parse_known_parts(input_text)

    assert "inspiration" in result
    assert "description" in result
    assert result["code"] == "console.log('Hello');"


def test_try_parse_code_from_start_tag():
    input_text = "<code>const x = 42;</code>"
    result = try_parse_code_from_start_tag(input_text)
    assert result == "const x = 42;</code>"


def test_try_parse_code_from_hash_tick_block():
    input_text = textwrap.dedent("""\
    Some text    ```javascript
    const x = 42;
    console.log(x);    ```
    More text
    """)

    result = try_parse_code_from_hash_tick_block(input_text)
    assert result == "const x = 42;\nconsole.log(x);"
