"""Provider-specific Chat request serialization and bounded public diagnostics.

No permissions, model fallback, retries, raw response logging or tool rewriting.
"""
from collections import Counter
from collections.abc import Iterable, Mapping
import re

DASHSCOPE_ADAPTER = 'dashscope-system-v1'
ERROR_SCHEMA = 'dscg.api-error.v1'
_ROLES = frozenset({'system', 'developer', 'user', 'assistant', 'tool', 'function', 'other'})


def _token(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:\[\]-]{1,96}', value) else None


def _role_counts(messages):
    if not isinstance(messages, (list, tuple)):
        return None
    return dict(Counter(m.get('role') if isinstance(m, Mapping) and
                        isinstance(m.get('role'), str) and m['role'] in _ROLES else 'other'
                        for m in messages))


def api_error_diagnostics(exc, messages=None):
    """Return whitelisted metadata, never an exception string/body or content."""
    stored = getattr(exc, '_dscg_api_error', None)
    status = getattr(exc, 'status_code', None)
    if not isinstance(stored, dict) and messages is None and type(status) is not int:
        return None
    roles = stored.get('request_role_counts') if isinstance(stored, dict) else None
    if not (isinstance(roles, dict) and all(k in _ROLES and type(v) is int and v >= 0 for k, v in roles.items())):
        roles = _role_counts(messages)
    body = getattr(exc, 'body', None)
    body = body if isinstance(body, dict) else {}
    error = body.get('error') if isinstance(body.get('error'), dict) else body
    return {'schema_version': ERROR_SCHEMA,
            'http_status': status if type(status) is int and 100 <= status <= 599 else None,
            'provider_error_code': _token(error.get('code', getattr(exc, 'code', None))),
            'provider_error_param': _token(error.get('param', getattr(exc, 'param', None))),
            'request_role_counts': dict(roles) if roles is not None else None}


def attach_api_error(exc, messages):
    detail = api_error_diagnostics(exc, messages)
    try:
        exc._dscg_api_error = detail
    except (AttributeError, TypeError):
        pass
    return detail


class _Proxy:
    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        return getattr(self._target, name)


class _Completions(_Proxy):
    def create(self, *args, **kwargs):
        messages = kwargs.get('messages')
        if isinstance(messages, Iterable) and not isinstance(messages, (str, bytes, Mapping)):
            # Materialize iterators once; leave source messages/content untouched.
            messages = [dict(m, role='system') if isinstance(m, Mapping) and m.get('role') == 'developer'
                        else m for m in messages]
            kwargs['messages'] = messages
        try:
            return self._target.create(*args, **kwargs)
        except Exception as exc:
            attach_api_error(exc, messages)
            raise


class _Chat(_Proxy):
    @property
    def completions(self):
        return _Completions(self._target.completions)


class DashScopeChatClient(_Proxy):
    @property
    def chat(self):
        return _Chat(self._target.chat)

    def with_options(self, *args, **kwargs):
        return type(self)(self._target.with_options(*args, **kwargs))

    copy = with_options

    def __enter__(self):
        self._target.__enter__()
        return self

    def __exit__(self, *args):
        return self._target.__exit__(*args)
