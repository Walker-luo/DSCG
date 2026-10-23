"""Upgrade old authored tool-only fixtures when testing the new default protocol."""
import json
from copy import deepcopy


def step_content(content, request):
    try:
        packet = json.loads(request['messages'][-1]['content'])
        catalog = packet['available_tools']
        if not catalog or not all(isinstance(v, dict) and 'authorization' in v for v in catalog.values()):
            return content
        value = json.loads(content)
        if not isinstance(value, dict) or set(value) != {'tools'} or not isinstance(value['tools'], list):
            return content
        names = value['tools']
        if request.get('response_format', {}).get('json_schema', {}).get('name') == 'dscg_action_steps_v2' or 'do not output read-only steps' in request['messages'][0]['content']:
            names = [n for n in names if n not in catalog or catalog[n].get('authorization') != 'automatic_read']
            return json.dumps({'steps': [{'intent': 'Authored fixture task', 'tools': names}] if names else []})
        return json.dumps({'steps':[{'intent':'Authored fixture task','tools':names}], 'tools':names})
    except (KeyError, TypeError, ValueError):
        return content


def adapt_client(client):
    mock = client.chat.completions.create
    previous = mock.side_effect
    def create(*args, **kwargs):
        response = (previous(*args, **kwargs) if callable(previous) else
                    next(previous) if previous is not None else mock.return_value)
        if isinstance(response, BaseException):
            raise response
        response = deepcopy(response)
        if isinstance(response.choices, (tuple, list)) and response.choices:
            response.choices[0].message.content = step_content(response.choices[0].message.content, kwargs)
        return response
    mock.side_effect = create
    return client
