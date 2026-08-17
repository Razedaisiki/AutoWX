"""联网路由测试：关键词强制 + MiMo JSON 判断。"""
from autowx.ai.router import decide_web_search, should_force_search


class FakeRouter:
    def __init__(self, reply: str):
        self._reply = reply

    def chat(self, messages):
        return self._reply


def test_force_search_keyword_hit():
    assert should_force_search("搜一下最新新闻")
    assert should_force_search("今天天气怎么样")
    assert should_force_search("帮我查一下")


def test_force_search_keyword_miss():
    assert not should_force_search("1+1 等于几")
    assert not should_force_search("写一段代码")


def test_decide_search_true():
    router = FakeRouter('{"search": true, "query": "OpenCode Go models"}')

    decision = decide_web_search(router, "OpenCode 有哪些新模型")

    assert decision.should_search is True
    assert decision.query == "OpenCode Go models"
    assert decision.reason == "router"


def test_decide_search_false():
    router = FakeRouter('{"search": false, "query": ""}')

    decision = decide_web_search(router, "1+1 等于几")

    assert decision.should_search is False


def test_decide_search_strips_code_fence():
    router = FakeRouter('```json\n{"search": true, "query": "天气"}\n```')

    decision = decide_web_search(router, "北京今天天气")

    assert decision.should_search is True
    assert decision.query == "天气"


def test_decide_search_fallback_on_bad_json():
    router = FakeRouter("not json at all")

    decision = decide_web_search(router, "你好")

    assert decision.should_search is False
    assert decision.query == "你好"
    assert decision.reason == "router-fallback"
