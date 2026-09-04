import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load_tool(name: str):
    path = ROOT / "dev" / "sdd" / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_step13_manifest_has_canonical_fields():
    manifest = json.loads((ROOT / "dev" / "step13" / "STEP.json").read_text(encoding="utf-8"))
    validator = load_tool("validate_step")
    assert validator._validate_schema(manifest) == []


def test_step12_cannot_validate_as_done():
    validator = load_tool("validate_step")
    errors = validator.validate_step(ROOT / "dev" / "step12", "done")
    assert errors
    assert any("missing required fields" in error or "Gate A is not approved" in error for error in errors)


def test_fully_completed_step_can_pass_done(tmp_path):
    source = ROOT / "dev" / "step13"
    target = tmp_path / "step14"
    import shutil

    shutil.copytree(source, target)
    manifest = json.loads((target / "STEP.json").read_text(encoding="utf-8"))
    manifest.update({"step": 14, "status": "DONE", "readiness": "YES"})
    for gate_name in ("gate_a", "gate_b", "gate_c"):
        manifest[gate_name].update({"status": "APPROVED", "approved_by": "test", "approved_at": "2026-09-05T00:00:00Z"})
    (target / "STEP.json").write_text(json.dumps(manifest), encoding="utf-8")
    acceptance = (target / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8").replace("- [ ]", "- [x]")
    (target / "ACCEPTANCE_CRITERIA.md").write_text(acceptance, encoding="utf-8")
    plan = (target / "PLAN.md").read_text(encoding="utf-8").replace("| PLANNED |", "| PASS |")
    (target / "PLAN.md").write_text(plan, encoding="utf-8")
    traceability = (target / "TRACEABILITY.md").read_text(encoding="utf-8")
    traceability = traceability.replace("| PLANNED |", "| PASS |").replace("| BLOCKED |", "| PASS |")
    (target / "TRACEABILITY.md").write_text(traceability, encoding="utf-8")

    assert load_tool("validate_step").validate_step(target, "done") == []


def test_traceability_rejects_unchecked_status(tmp_path):
    source = ROOT / "dev" / "step13"
    target = tmp_path / "step13"
    target.mkdir()
    for name in ("REQUEST.md", "REQUIREMENT.md", "PLAN.md", "ACCEPTANCE_CRITERIA.md", "TRACEABILITY.md", "RESULT.md", "STEP.json"):
        (target / name).write_text((source / name).read_text(encoding="utf-8"), encoding="utf-8")
    manifest = json.loads((target / "STEP.json").read_text(encoding="utf-8"))
    manifest.update({"readiness": "YES", "requirements": ["REQ-013-001"], "acceptance": ["AC-013-001"], "evidence": ["E-013-001"]})
    manifest["gate_a"]["status"] = "APPROVED"
    (target / "STEP.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert any("Traceability row is not PASS" in error for error in load_tool("validate_step").validate_step(target, "done"))


def test_new_step_uses_highest_numeric_directory():
    assert load_tool("new_step").next_step_number() == 15


def test_changed_step_names_selects_only_canonical_step_paths():
    validator = load_tool("validate_changed_steps")
    assert validator.changed_step_names([
        "dev/step14/PLAN.md",
        "dev/hec/web/frontend/js/app.js",
        "dev/step12/RESULT.md",
        "README.md",
    ]) == ["step12", "step14"]


def test_new_step_generates_manifest_and_readme_row(tmp_path, monkeypatch):
    generator = load_tool("new_step")
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("| Krok | Obsah | Stav |\n|---|---|---|\n| [`step01/`](step01/) | Existing | done |\n", encoding="utf-8")
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    monkeypatch.setattr(generator, "TEMPLATES", templates)
    monkeypatch.setattr(generator, "README", readme)
    target = generator.create_step(2)
    manifest = json.loads((target / "STEP.json").read_text(encoding="utf-8"))
    assert manifest["step"] == 2
    assert load_tool("validate_step")._validate_schema(manifest) == []
    assert (target / "PLAN.md").exists()
    assert "step02/" in readme.read_text(encoding="utf-8")


def test_new_step_rejects_existing_target(tmp_path, monkeypatch):
    generator = load_tool("new_step")
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    (tmp_path / "dev" / "step02").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        generator.create_step(2)


def test_pr_renderer_projects_validation_evidence(tmp_path):
    renderer = load_tool("render_pr")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    renderer.RUNTIME = runtime
    validation = {"status": "PASS", "counts": {"total": 2, "passed": 2, "failed": 0}}
    (runtime / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
    output = tmp_path / "pr_body.md"
    renderer.render(ROOT / "dev" / "step13", output)
    text = output.read_text(encoding="utf-8")
    assert "Step 13 validation evidence" in text
    assert "2/2 checks passed" in text
