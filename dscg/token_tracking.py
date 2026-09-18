# ==========================================
# 提取到外部的辅助代理类
# ==========================================
class _CompletionsProxy:
    def __init__(self, completions, tracker):
        self._completions = completions
        self._tracker = tracker

    def create(self, *args, **kwargs):
        # 1. 正常发起原始请求
        response = self._completions.create(*args, **kwargs)
        # 2. 拦截并提取消耗的 Token
        if hasattr(response, 'usage') and response.usage:
            self._tracker.total_prompt_tokens += response.usage.prompt_tokens
            self._tracker.total_completion_tokens += response.usage.completion_tokens
        return response

class _ChatProxy:
    def __init__(self, chat, tracker):
        self._chat = chat
        self._tracker = tracker

    @property
    def completions(self):
        # 直接调用外部的 _CompletionsProxy，去掉 self.
        return _CompletionsProxy(self._chat.completions, self._tracker)

# ==========================================
# 主 Token 追踪器
# ==========================================
class TokenTrackerClient:
    """
    一个无入侵的 OpenAI Client 包装器，用于拦截并统计全局 Token 消耗。
    """
    def __init__(self, client):
        self._client = client
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def get_total_tokens(self):
        return self.total_prompt_tokens + self.total_completion_tokens

    def reset(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    @property
    def chat(self):
        # 直接调用外部的 _ChatProxy，去掉 self.
        return _ChatProxy(self._client.chat, self)