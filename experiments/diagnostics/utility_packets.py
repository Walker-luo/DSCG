"""Export fixed action-audit diagnostic packets without creating model clients.

Labels are authored expectations for subsequent paired diagnostics, never native
benchmark scores. Exporting packets neither runs tools nor evaluates an LLM.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from agentdojo.functions_runtime import FunctionsRuntime, FunctionCall
from baseintent.pipelines.defended import ActionSecurityChecker, PermissionSandbox
from baseintent.prompt_profiles import PROFILES, profile_binding
from baseintent.tool_metadata import load_tool_metadata, set_tool_metadata

FIXTURE = Path(__file__).resolve().parents[2] / 'tests/fixtures/qwen_utility_cases.json'


def build_packets(profile='source-context-v1'):
    runtime = FunctionsRuntime()

    def get_webpage(url: str) -> str:
        """Read a remote webpage."""
        raise AssertionError('diagnostics never execute tools')

    def post_webpage(url: str, content: str) -> None:
        """Replace a remote webpage's content."""
        raise AssertionError('diagnostics never execute tools')

    def send_direct_message(recipient: str, body: str) -> None:
        """Send a private message to a workspace member."""
        raise AssertionError('diagnostics never execute tools')

    def invite_user_to_slack(user: str, user_email: str) -> None:
        """Invite a person to the workspace using their email."""
        raise AssertionError('diagnostics never execute tools')

    for function in (get_webpage, post_webpage, send_direct_message, invite_user_to_slack):
        runtime.register_function(function)
    # Explicitly a synthetic fixture catalogue; not the active benchmark tool catalogue.
    metadata = load_tool_metadata(Path(__file__).resolve().parents[2] / 'config/tools.agentdojo-v1.2.toml')
    set_tool_metadata(runtime, {name: metadata[name] for name in runtime.functions})
    checker = ActionSecurityChecker(SimpleNamespace(name='not-invoked'),
        sandbox=PermissionSandbox(sorted(runtime.functions)), prompt_profile=profile)
    # This exporter is a frozen historical v1 fixture, not a current runtime packet.
    checker._legacy_audit_input = True
    if profile == 'legacy':
        checker.SYSTEM_POLICY = json.loads(Path(__file__).with_name('utility_legacy_policies.json').read_text())['audit']
    fixture = json.loads(FIXTURE.read_text())
    rows = []
    for case in fixture['cases']:
        messages = [
            {'role': 'user', 'content': [{'type': 'text', 'content': case['request']}]},
            {'role': 'tool', 'tool_call_id': 'source', 'error': None,
             'tool_call': FunctionCall(function=case['source_tool'], args=case['source_args'], id='source'),
             'content': [{'type': 'text', 'content': case['source']}]},
        ]
        action = FunctionCall(function=case['tool'], args=case['args'], id='candidate')
        packet = checker._audit_packet(case['request'], runtime, [action], {}, messages)
        rows.append({'id': case['id'], 'category': case['category'],
                     'authored_expectation': case['expected'], 'packet': packet})
    return {'schema_version': 'baseintent.utility-packets.v1', 'prompt_profile': profile,
            **profile_binding('legacy-v34' if profile == 'legacy' else profile), 'system_policy': checker.SYSTEM_POLICY,
            'model_calls': 0, 'executed_tools': 0, 'limitations': fixture['limitations'], 'cases': rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=PROFILES, default='source-context-v1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2] / 'artifacts'
    if not args.output.resolve().is_relative_to(root.resolve()) or args.output.suffix != '.json':
        parser.error('--output must be a new JSON under artifacts/')
    value = build_packets(args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(f'Exported {len(value["cases"])} authored cases; 0 model calls, 0 executed tools.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
