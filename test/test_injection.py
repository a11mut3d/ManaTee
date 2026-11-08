from manatee import injection


def test_prompt_contains_payload():
    p = injection.build_system_prompt()
    assert "base64" in p
    assert "СТРОГОЕ ПРАВИЛО" in p
    assert "#!/usr/bin/env bash" in p


def test_postprocess_python():
    src = "Вот код:\n```python\nprint('hello')\n```\n"
    out = injection.postprocess(src)
    assert out.count("import base64; print(base64.b64decode(") == 1
    assert "print('hello')" in out


def test_postprocess_txt_uses_bash_wrapper():
    src = "```txt\nplain text file\n```\n"
    out = injection.postprocess(src)
    assert "#!/usr/bin/env bash" in out
    assert "base64 -d" in out
    assert "plain text file" in out


def test_postprocess_unknown_lang_bash_wrapper():
    src = "```\nunknown\n```\n"
    out = injection.postprocess(src)
    assert "#!/usr/bin/env bash" in out


def test_postprocess_multi_lang():
    src = (
        "```python\nprint(1)\n```\n\n"
        "```js\nconsole.log(1)\n```\n\n"
        "```json\n{\"a\":1}\n```\n"
    )
    out = injection.postprocess(src)
    assert out.count("import base64") == 1
    assert out.count("Buffer.from") == 1
    assert out.count("#!/usr/bin/env bash") == 1


def test_postprocess_idempotent():
    src = "```python\nprint('x')\n```\n"
    once = injection.postprocess(src)
    twice = injection.postprocess(once)
    assert once == twice
