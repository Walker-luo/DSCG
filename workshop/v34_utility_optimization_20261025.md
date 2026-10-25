# v3.4 utility optimization implementation plan

> Execute inline with superpowers:executing-plans. User approved implementation and real Qwen validation; no commits or branch changes.

**Goal:** Implement analysis/v3-4.md §4 using the shared production factory, then measure typical banking/Slack trajectories with qwen3.7-flash.

**Architecture:** Reuse the existing exhaustive Boolean permission protocol for a single L2 call, avoiding omitted tools hidden by step generation. A shared host predicate exempts registered, schema-valid public/internal reads in every router mode; mixed-batch audit reviews only other calls while whole-batch authorization, receipt binding and execution order remain intact. Private reads and effects receive a staged four-field audit; private deny is enforced.

**Spec:** [analysis/v3-4.md](../analysis/v3-4.md#4-优化方案与验证顺序已实施). Candidate identity DSCG_v3.4.1; historical outputs remain untouched.

**Constraints:** Current checkout, preserve dirty documents and plan.md deletion; no model/provider change, no retries, grants frozen, no task-ID rules, parameter repair, obligation ledger or new recovery. Original HEAD source archived under fresh artifacts for online control. Model replies only in existing diagnostics.

**Review focus:** schema-invalid/unauthorized mixed batch rejects all; receipt mutation rejects all; exempt read survives valid denial of effect; private deny/abstain block; protocol identities match actual requests and cache bindings.

## Tasks

1. [x] Add failing behavior tests in tests/test_read_exemptions.py for all modes, arbitrary web source/sink, mixed batches, private denial, unauthorized batches and receipt mutation. Run via ipi Python and save RED log.
2. [x] In dscg/audit_router.py share is_exempt_read(call,runtime); update eligibility and policy identity. In defended.py audit only nonexempt candidates but bind full batch; recompute exemptions at Monitor after authority/handoff checks. Run relevant routing/monitor regressions.
3. [x] Reuse permission_schema/parse_permissions and AUTH_POLICY from intent_evidence for default L2; retain old parser compatibility only for explicitly legacy test paths. Update identity/accounting and regression fixtures. Restructure default L3 packet by current read/effect stage, actual arguments and paired evidence; keep strict verdict only. Remove private-read deny override. Set new framework identity.
4. [x] Freeze ≥18 distinct scored typical cases, clean/ignore_previous/tool_knowledge across banking and Slack (travel small control if needed). Run archived v3.4 and new version through shared native runner in fresh directories. Run prompt-only completion comparison separately where informative. Record attempts/completions/valid/errors, native grades, raw replies, actual calls/usage and outbound settings.
5. [x] Run targeted and broader offline checks, review changes, update analysis and DV_STATE, deliver completed report with exact commands/exit codes/artifacts/hashes and limits. Do not claim general safety or full benchmark coverage.

**Validation:** Offline routing/authorization/error tests establish engineering contracts only. Online scored trajectories establish this bounded sample's behavior; errors retain null efficacy and are never counted as defense successes. Expand fresh samples if failures reveal unresolved behavior; no closed campaign budget reused.

## Execution ledger

- Native execution in existing workshop checkout; dirty analysis documents and plan.md deletion preserved. No staging or commits.
- Ruling: reuse tool-permissions-v1 rather than generate more action steps. Complete Boolean keys prevent silent omissions without adding a model call.
- RED→GREEN: tests/test_read_exemptions.py covers all-mode exemption, mixed subset, private deny, receipt mutation, unauthorized/schema-invalid batches, and factory off handoff; complete-permission tests cover missing/unknown/nonboolean keys.
- Review caught factory-off verifier, absent batch schema check, opt-in cache binding and report-policy migration; all fixed with regression coverage.
- Archived HEAD full offline control: 716 tests, 23 failures/6 errors/13 skips; I3 failures already present. Final current verification727 tests:704 pass,5 failures,5 errors,13 skips, all10 residualI3 cases reproduced at HEAD; do not claim whole suite green.
- Online: control_02, l2, read, candidate each completed 18/18 valid; utilities 5/8/8/15 respectively, attacked ASR each0/12. completion arm completed18/18 valid, utility15/18, ASR0/12; no added utility, default remains off. No production behavior changed during scored runs; later edits preserve frozen legacy diagnostic bytes/profile cache identity and update readers/tests.
- Initial automatic review rejected online dispatch citing a closed campaign balance; clarified explicit fresh-task authorization AGENTS90/93 and new user request, same action accepted. First accepted launch failed before calls because snapshot lacked public backend lock; preserved it and used fresh control_02.
