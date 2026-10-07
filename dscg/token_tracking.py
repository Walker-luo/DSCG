"""OpenAI-compatible token/API accounting; missing usage is explicit."""
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from time import perf_counter

class _CompletionsProxy:
    def __init__(self, completions, tracker):
        self._completions, self._tracker = completions, tracker

    def create(self, *args, **kwargs):
        tracker = self._tracker
        record = tracker._phases[tracker._phase.get()]
        record['api_calls'] += 1
        started = perf_counter()
        try:
            response = self._completions.create(*args, **kwargs)
            usage = getattr(response, 'usage', None)
            if usage:
                prompt = usage.prompt_tokens or 0
                completion = usage.completion_tokens or 0
                tracker.total_prompt_tokens += prompt
                tracker.total_completion_tokens += completion
                record['prompt_tokens'] += prompt
                record['completion_tokens'] += completion
                record['total_tokens'] += prompt + completion
            else:
                record['missing_usage_calls'] += 1
            return response
        except Exception:
            record['failed_calls'] += 1
            raise
        finally:
            record['latency_ms'] += round((perf_counter() - started) * 1000, 3)

class _ChatProxy:
    def __init__(self, chat, tracker):
        self._chat, self._tracker = chat, tracker
    @property
    def completions(self):
        return _CompletionsProxy(self._chat.completions, self._tracker)

class TokenTrackerClient:
    def __init__(self, client, default_phase='generation'):
        self._client = client
        self._phase = ContextVar('dscg_api_phase', default=default_phase)
        self.reset()

    def get_total_tokens(self):
        return self.total_prompt_tokens + self.total_completion_tokens

    def reset(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self._phases = defaultdict(lambda: dict.fromkeys(
            ('api_calls','failed_calls','missing_usage_calls','prompt_tokens',
             'completion_tokens','total_tokens','latency_ms'), 0))

    @contextmanager
    def phase(self, name):
        token = self._phase.set(name)
        try: yield
        finally: self._phase.reset(token)

    def snapshot(self):
        return deepcopy(dict(self._phases))

    @property
    def chat(self):
        return _ChatProxy(self._client.chat, self)
