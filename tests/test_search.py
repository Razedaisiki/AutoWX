"""搜索与应答 fallback 测试。"""
from autowx.ai.responder import WebAwareChat
from autowx.ai.search import format_search_context


def test_format_search_context():
    results = [
        {"title": "标题1", "content": "内容1", "url": "https://a.com"},
        {"title": "标题2", "content": "内容2", "url": "https://b.com"},
    ]

    text = format_search_context(results)

    assert "[1] 标题1" in text
    assert "来源: https://a.com" in text
    assert "[2] 标题2" in text
    assert "来源: https://b.com" in text


class _FakeAnswer:
    def __init__(self):
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return "回答"


class _FakeRouter:
    def chat(self, messages):
        return '{"search": false, "query": ""}'


class _FakeSearch:
    def __init__(self, result: str):
        self._result = result

    def search(self, query):
        return self._result


def test_web_aware_no_search():
    answer = _FakeAnswer()
    chat = WebAwareChat(answer, _FakeRouter(), _FakeSearch(""))

    reply = chat.chat([{"role": "user", "content": "1+1 等于几"}])

    assert reply == "回答"
    assert len(answer.calls) == 1


def test_web_aware_search_failure_falls_back():
    """搜索抛异常时，仍退回主模型正常回答。"""

    class _BoomSearch:
        def search(self, query):
            raise RuntimeError("tavily down")

    answer = _FakeAnswer()
    chat = WebAwareChat(answer, _FakeRouter(), _BoomSearch())

    # 命中关键词，触发搜索 → 搜索抛异常 → fallback
    reply = chat.chat([{"role": "user", "content": "搜一下最新新闻"}])

    assert reply == "回答"
    assert len(answer.calls) == 1


def test_web_aware_search_augments_context():
    answer = _FakeAnswer()
    router = _FakeRouter()

    class _KeywordRouter:
        pass

    # 用关键词触发搜索
    chat = WebAwareChat(
        answer,
        router,
        _FakeSearch("[1] 标题\n内容\n来源: https://a.com"),
    )

    reply = chat.chat([{"role": "user", "content": "搜一下 OpenCode"}])

    assert reply == "回答"
    # 搜索命中时，主模型收到的是带系统资料前缀的消息
    augmented = answer.calls[-1]
    assert augmented[0]["role"] == "system"
    assert "[1] 标题" in augmented[0]["content"]
