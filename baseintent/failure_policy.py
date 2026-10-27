"""Public failure provenance; blocked tool returns are never execution evidence."""

FAILURE_POLICY = 'framework-failure-native-scoring-v1'
BLOCK_PREFIXES = ('L2_BLOCKED:', 'L3_BLOCKED:', 'MONITOR_BLOCKED:', 'BASEINTENT_BLOCKED:', 'DSCG_BLOCKED:')
MODULE_NAMES = {'L1': 'L1 Input Isolation', 'L2': 'L2 Authorization',
                'L3': 'L3 Security Check', 'Monitor': 'Reference Monitor',
                'Intent Progress': 'Intent Progress'}

# Only received model-output defects and bounded unsuccessful attempts qualify.
# Input construction, changed catalogues, I/O and API failures remain errors.
FRAMEWORK_FAILURE_CODES = frozenset({
    'AUTH_INVALID_INTENTS', 'AUTH_INVALID_GLOBAL_TOOLS', 'INTENT_NO_CHOICE',
    'INTENT_INCOMPLETE', 'INTENT_INVALID_JSON', 'INTENT_INVALID_PROGRESS',
    'INTENT_NO_PROGRESS', 'INTENT_ITERATION_BOUND',
})


def is_blocked_error(error):
    return isinstance(error, str) and (error in ('BASEINTENT_BLOCKED','DSCG_BLOCKED') or error.startswith(BLOCK_PREFIXES))


def block_error(module, reason):
    prefix = {'L2': 'L2', 'L3': 'L3', 'Monitor': 'MONITOR'}[module]
    return f'{prefix}_BLOCKED:{reason}'
