"""Check this documentation-only handoff; does not run a model or tools."""

import hashlib
import json
import re
import subprocess
from pathlib import Path


DSCG = Path(__file__).resolve().parents[4]
RESEARCH = DSCG.parent / "research"
OUT = Path(__file__).resolve().parent
BASE = "5e382f946b4554162fcd84eaec26b1d8c60332ce"
RUNTIME_SHA = "75583be0d62b2a478f9d070f79b7aa84dffd71b12a21931e60c696273163f7b0"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_local_links(path, text):
    checked = []
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#")):
            continue
        target = target.split("#", 1)[0]
        dest = (path.parent / target).resolve()
        assert dest.exists(), (path, label, target)
        checked.append({"source": str(path), "target": str(dest)})
    return checked


def main():
    assert DSCG == Path("/Users/luo/Desktop/AgentDefence/DSCG")
    doc_path = RESEARCH / "paper/3_layer_opt.md"
    catalog_path = RESEARCH / "paper/3_layer_sources_20261008.json"
    doc = doc_path.read_text()
    catalog = json.loads(catalog_path.read_text())
    refs = dict(re.findall(r"^\[([^\]]+)\]: (https://\S+)$", doc, re.M))
    sources = catalog["sources"]
    assert len(sources) == catalog["primary_paper_count"] == 11
    assert len({s["id"] for s in sources}) == 11
    assert {s["id"]: s["primary_url"] for s in sources} == refs
    for source in sources:
        assert source["existence_and_claims_checked"]
        assert source["verified_date"] == "2026-10-08"
        assert source["title"] in doc
        assert all(author in doc for author in source["authors_first_three"])
        assert source["read_locations"] and source["limitations"]
    for ref in re.findall(r"\[[^\]]+\]\[([^\]]+)\]", doc):
        assert ref in refs, ref
    links = check_local_links(doc_path, doc)
    readme_path, agents_path = DSCG / "README.md", DSCG / "AGENTS.md"
    readme, agents = readme_path.read_text(), agents_path.read_text()
    new_readme = next(line for line in readme.splitlines() if "三层优化的[" in line)
    new_agents = agents.split("## Three-layer research candidates (2026-10-08)", 1)[1]
    links += check_local_links(readme_path, new_readme)
    links += check_local_links(agents_path, new_agents)
    assert "方案尚未实现" in new_readme and "当前默认仍是上述两层" in new_readme
    assert "unimplemented hypotheses" in new_agents and "retries=0" in new_agents
    assert "主要安全候选" in doc and "最多 1 次" in doc
    assert "仍锁定" in doc and "有效 24 条中仍有 8 个范围缺口" in doc
    assert "DataFilter v2 表 VIII" in doc and "93%" in doc and "83%" in doc
    assert "benchmark 的隐藏目标状态仅作评分，不输入 Agent" in doc
    assert sha(DSCG / "dscg/pipelines/defended.py") == RUNTIME_SHA
    changed = git(DSCG, "diff", "--name-only", BASE).splitlines()
    allowed = {"README.md", "AGENTS.md"}
    prefix = "examples/results/framework_optimization/20261008_three_layer_research/"
    assert all(p in allowed or p.startswith(prefix) for p in changed), changed
    route = RESEARCH / "technical_route.md"
    route_head = subprocess.check_output(["git", "-C", str(RESEARCH), "show", "HEAD:technical_route.md"])
    assert route.read_bytes() == route_head, "Research route was modified"
    paths = [doc_path, catalog_path, readme_path, agents_path, Path(__file__).resolve(), route]
    result = {
        "status": "pass",
        "scope": "document links, primary-source catalog consistency and unchanged runtime/route; not literature reproduction or benchmark validation",
        "base_dscg_commit": BASE,
        "validation_dscg_head": git(DSCG, "rev-parse", "HEAD").strip(),
        "validation_research_head": git(RESEARCH, "rev-parse", "HEAD").strip(),
        "verified_primary_papers": 11,
        "checked_local_links": links,
        "new_model_calls": 0,
        "new_benchmark_samples": 0,
        "runtime_tests_run": 0,
        "runtime_sha256_unchanged": RUNTIME_SHA,
        "changed_tracked_dscg_files_since_base": changed,
        "dscg_worktree_at_validation": git(DSCG, "status", "--short"),
        "research_worktree_at_validation": git(RESEARCH, "status", "--short"),
        "artifacts_sha256": {str(p): sha(p) for p in paths},
        "limitations": [
            "Checks do not independently reproduce paper experiments or validate source completeness.",
            "No third layer has been implemented; I3 remains partial and real E0 remains pending.",
            "Historical benchmark counts are cited, not newly measured.",
            "Research repository had unrelated dirty changes before this phase; only new research files are staged."
        ],
    }
    (OUT / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "papers": 11, "local_links": len(links),
                      "runtime_unchanged": True, "route_unchanged": True, "new_model_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
