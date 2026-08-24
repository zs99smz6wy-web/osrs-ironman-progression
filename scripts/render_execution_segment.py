"""Render a research-only execution segment as a standalone local HTML reader."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "research" / "execution-segments" / "post-tutorial-varrock-museum-proof.json"
DEFAULT_OUTPUT = ROOT / "route" / "previews" / "post-tutorial-varrock-museum-proof.html"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def list_items(items: list[str], *, class_name: str = "plain-list") -> str:
    if not items:
        return "<p class=\"muted\">None recorded.</p>"
    return f'<ul class="{class_name}">' + "".join(f"<li>{text(item)}</li>" for item in items) + "</ul>"


def coverage_badge(coverage: dict[str, Any]) -> str:
    status = str(coverage.get("status", "unresolved"))
    labels = {
        "normalized_action": "Normalized action",
        "sourced_unmodeled_substep": "Sourced substep",
        "unresolved": "Unresolved",
    }
    return f'<span class="badge badge-{text(status)}">{text(labels.get(status, status))}</span>'


def requirements_markup(requirements: dict[str, Any]) -> str:
    rows = []
    for label, key in (("Carried items", "carried_items"), ("Banked items", "banked_items")):
        values = requirements.get(key, [])
        content = ", ".join(text(item) for item in values) if values else "None recorded"
        rows.append(f"<dt>{label}</dt><dd>{content}</dd>")
    for label, key in (("Carried GP", "carried_gp"), ("Banked GP", "banked_gp")):
        rows.append(f"<dt>{label}</dt><dd>{text(requirements.get(key, 0))}</dd>")
    return '<dl class="requirements">' + "".join(rows) + "</dl>"


def checkpoint_markup(checkpoint: dict[str, Any]) -> str:
    coverage = checkpoint.get("coverage", {})
    return (
        '<li class="checkpoint-item">'
        f'<div class="item-line"><strong>{text(checkpoint.get("description", "Checkpoint"))}</strong>{coverage_badge(coverage)}</div>'
        f'<p class="boundary"><span>Boundary:</span> {text(coverage.get("boundary", "No boundary recorded."))}</p>'
        "</li>"
    )


def step_markup(step: dict[str, Any], segment_id: str, *, branch: bool = False) -> str:
    coverage = step.get("coverage", {})
    step_id = str(step.get("id", "step"))
    input_id = f"guide-{segment_id}-{step_id}".replace(":", "-")
    sequence = text(step.get("sequence", "?"))
    action_id = coverage.get("normalized_action_id")
    action = f'<p class="action-ref">Linked record: <code>{text(action_id)}</code></p>' if action_id else ""
    checkpoint_ids = step.get("checkpoint_ids", [])
    checkpoint_line = ""
    if checkpoint_ids:
        checkpoint_line = f'<p class="checkpoint-ref">Checkpoint: {", ".join(f"<code>{text(item)}</code>" for item in checkpoint_ids)}</p>'
    kind = " branch-step" if branch else ""
    return (
        f'<li class="step{kind}">'
        f'<input class="step-check" type="checkbox" id="{text(input_id)}" data-step-id="{text(step_id)}">'
        f'<label for="{text(input_id)}"><span class="step-number">{sequence}</span><span class="step-text">{text(step.get("instruction", ""))}</span></label>'
        f'<div class="step-meta">{coverage_badge(coverage)}</div>'
        f'{action}{checkpoint_line}'
        f'<p class="boundary"><span>Boundary:</span> {text(coverage.get("boundary", "No boundary recorded."))}</p>'
        "</li>"
    )


def render_segment(segment: dict[str, Any]) -> str:
    """Return a complete, self-contained HTML document for one segment."""
    name = str(segment.get("name", "Execution segment"))
    segment_id = str(segment.get("segment_id", "segment"))
    purpose = segment.get("purpose", {})
    starting = segment.get("starting_state", {})
    requirements = starting.get("requirements", {})
    checkpoints = [starting.get("geographic_checkpoint", {}), starting.get("bank_checkpoint", {})] + list(segment.get("checkpoints", []))
    main_steps = "".join(step_markup(step, segment_id) for step in segment.get("execution_steps", []))
    branches = segment.get("branches", [])
    branch_markup = ""
    for branch in branches:
        branch_steps = "".join(step_markup(step, segment_id, branch=True) for step in branch.get("steps", []))
        branch_markup += (
            '<section class="branch" aria-labelledby="optional-branch">'
            '<div class="section-heading"><h2 id="optional-branch">Optional branch</h2><span class="badge badge-unresolved">Player choice</span></div>'
            f'<p class="when"><strong>When:</strong> {text(branch.get("when", ""))}</p>'
            f'<ol class="steps branch-steps">{branch_steps}</ol>'
            f'<p class="boundary"><span>Boundary:</span> {text(branch.get("coverage", {}).get("boundary", "No boundary recorded."))}</p>'
            "</section>"
        )
    sources = "".join(
        '<li><a href="{url}" target="_blank" rel="noopener noreferrer">{identifier}</a>'
        '<p>{used_for}</p><small>Verified: {verified}</small></li>'.format(
            url=text(source.get("url", "")),
            identifier=text(source.get("id", "source")),
            used_for=text(source.get("used_for", "")),
            verified=text(source.get("verified_at", "unknown")),
        )
        for source in segment.get("source_catalog", [])
    )
    safety = segment.get("safety_hcim", {})
    passive = segment.get("passive_recurring_checks", [])
    passive_markup = "".join(
        '<li><strong>{identifier}</strong><dl class="policy">'
        '<dt>Trigger</dt><dd>{trigger}</dd><dt>Observe</dt><dd>{observe}</dd><dt>Policy</dt><dd>{policy}</dd>'
        "</dl></li>".format(
            identifier=text(item.get("id", "Passive check")),
            trigger=text(item.get("trigger_when", "")),
            observe=text(item.get("required_current_observation", "")),
            policy=text(item.get("interruption_policy", "")),
        )
        for item in passive
    )
    stops = segment.get("stop_reentry_conditions", {})
    estimate = segment.get("estimated_time", {})
    estimated_label = "Not estimated" if estimate.get("status") == "not_estimated" else "Sourced range"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>{text(name)} | OSRS progression research</title>
  <style>
    :root {{ --page: #111619; --panel: #192125; --panel-alt: #151c20; --line: #37444a; --text: #e8ede8; --muted: #aab6b4; --accent: #d6b45d; --green: #89b56e; --amber: #e5af53; --red: #dc7777; --focus: #f2d77d; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--page); color: var(--text); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
    a {{ color: #a9d5e3; }}
    a:focus-visible, button:focus-visible, input:focus-visible {{ outline: 3px solid var(--focus); outline-offset: 2px; }}
    code {{ color: #d9cb9b; overflow-wrap: anywhere; }}
    .shell {{ max-width: 1080px; margin: 0 auto; padding: 18px; display: grid; grid-template-columns: minmax(210px, 260px) minmax(0, 1fr); gap: 14px; }}
    .sidebar, .reader {{ border: 1px solid var(--line); border-radius: 6px; background: var(--panel); }}
    .sidebar {{ align-self: start; position: sticky; top: 14px; padding: 16px; }}
    .reader {{ overflow: hidden; }}
    .titlebar {{ padding: 18px 20px; background: #202a2f; border-bottom: 1px solid var(--line); }}
    .eyebrow {{ margin: 0 0 7px; color: var(--accent); font-size: 12px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }}
    h1, h2, h3 {{ margin: 0; line-height: 1.25; }} h1 {{ font-size: 22px; }} h2 {{ font-size: 16px; }} h3 {{ font-size: 14px; }}
    .title-meta, .muted, small {{ color: var(--muted); }} .title-meta {{ margin: 8px 0 0; font-size: 13px; }}
    .badge {{ display: inline-flex; align-items: center; min-height: 24px; padding: 2px 7px; border: 1px solid currentColor; border-radius: 4px; font-size: 12px; font-weight: 700; white-space: nowrap; }}
    .badge-normalized_action {{ color: var(--green); }} .badge-sourced_unmodeled_substep {{ color: var(--accent); }} .badge-unresolved {{ color: var(--amber); }}
    .status-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }}
    .nav-title {{ font-size: 12px; color: var(--muted); margin: 0 0 7px; text-transform: uppercase; letter-spacing: .06em; }}
    .sidebar nav a {{ display: block; padding: 5px 0; color: var(--text); text-decoration: none; }} .sidebar nav a:hover {{ color: var(--accent); }}
    .reset {{ width: 100%; min-height: 36px; margin-top: 18px; border: 1px solid var(--line); border-radius: 4px; background: #263238; color: var(--text); font: inherit; cursor: pointer; }} .reset:hover {{ border-color: var(--accent); }}
    .local-note {{ margin: 10px 0 0; font-size: 12px; color: var(--muted); }}
    .section, .branch {{ padding: 18px 20px; border-bottom: 1px solid var(--line); }} .section:last-child {{ border-bottom: 0; }}
    .section-heading, .item-line {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }}
    .section-heading {{ margin-bottom: 10px; }} .section p {{ margin: 7px 0; }}
    .plain-list, .checkpoints, .sources {{ margin: 10px 0 0; padding-left: 21px; }} .plain-list li + li {{ margin-top: 6px; }}
    .requirements {{ display: grid; grid-template-columns: minmax(110px, 150px) minmax(0, 1fr); margin: 12px 0 0; border-top: 1px solid var(--line); }} .requirements dt, .requirements dd {{ margin: 0; padding: 8px 0; border-bottom: 1px solid var(--line); }} .requirements dt {{ color: var(--muted); }}
    .checkpoint-item {{ padding: 10px 0; border-bottom: 1px solid var(--line); }} .checkpoint-item:last-child {{ border-bottom: 0; }}
    .boundary {{ color: var(--muted); font-size: 13px; }} .boundary span {{ color: var(--amber); font-weight: 700; }}
    .steps {{ list-style: none; padding: 0; margin: 0; counter-reset: guide; }} .step {{ display: grid; grid-template-columns: 22px minmax(0, 1fr) auto; column-gap: 10px; padding: 13px 0; border-top: 1px solid var(--line); }}
    .step-check {{ width: 18px; height: 18px; margin: 2px 0 0; accent-color: var(--green); }} .step label {{ display: flex; gap: 9px; cursor: pointer; }} .step-number {{ flex: 0 0 22px; color: var(--accent); font-weight: 700; }} .step-text {{ min-width: 0; }}
    .step:has(.step-check:checked) .step-text {{ color: var(--muted); text-decoration: line-through; }} .step:has(.step-check:checked) .step-number {{ color: var(--green); }}
    .step-meta {{ grid-column: 3; }} .step > p {{ grid-column: 2 / -1; margin: 7px 0 0; }} .action-ref, .checkpoint-ref {{ color: var(--muted); font-size: 13px; }}
    .branch {{ background: var(--panel-alt); }} .when {{ margin: 0 0 10px; }} .branch-steps .step {{ border-color: var(--line); }}
    .policy {{ margin: 8px 0 0; display: grid; grid-template-columns: 80px minmax(0, 1fr); gap: 6px 10px; }} .policy dt {{ color: var(--muted); }} .policy dd {{ margin: 0; }}
    .sources li {{ padding: 10px 0; border-bottom: 1px solid var(--line); }} .sources li:last-child {{ border-bottom: 0; }} .sources p {{ margin: 4px 0; }}
    .reader-footer {{ padding: 14px 20px; color: var(--muted); font-size: 13px; background: var(--panel-alt); }}
    @media (max-width: 760px) {{ .shell {{ display: block; padding: 10px; }} .sidebar {{ position: static; margin-bottom: 10px; }} .sidebar nav {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 14px; }} .titlebar, .section, .branch {{ padding: 15px; }} .step {{ grid-template-columns: 22px minmax(0, 1fr); }} .step-meta {{ grid-column: 2; margin-top: 7px; }} .requirements {{ grid-template-columns: 105px minmax(0, 1fr); }} }}
  </style>
</head>
<body>
  <main class="shell">
    <aside class="sidebar" aria-label="Guide navigation">
      <p class="nav-title">Research reader</p>
      <nav>
        <a href="#purpose">Purpose</a><a href="#preparation">Preparation</a><a href="#checkpoints">Checkpoints</a><a href="#steps">Steps</a><a href="#safety">Safety</a><a href="#sources">Sources</a>
      </nav>
      <button class="reset" type="button" id="reset-checks">Reset step checks</button>
      <p class="local-note" id="storage-status">Step checks are stored only in this browser.</p>
    </aside>
    <article class="reader">
      <header class="titlebar">
        <p class="eyebrow">OSRS progression research</p>
        <h1>{text(name)}</h1>
        <p class="title-meta"><code>{text(segment_id)}</code></p>
        <div class="status-row"><span class="badge badge-unresolved">Research-only</span><span class="badge badge-unresolved">{text(segment.get("status", "unknown"))}</span><span class="badge badge-unresolved">{text(estimated_label)}</span></div>
      </header>
      <section class="section" id="purpose">
        <div class="section-heading"><h2>Purpose and why now</h2><span class="badge badge-unresolved">Not route selection</span></div>
        <h3>What this fragment documents</h3>{list_items(list(purpose.get("accomplishes", [])))}
        <h3>When it may be relevant</h3>{list_items(list(purpose.get("account_applicability", [])))}
        <p class="boundary"><span>Timing boundary:</span> {text(purpose.get("timing_observation", "No timing observation recorded."))}</p>
      </section>
      <section class="section" id="preparation">
        <div class="section-heading"><h2>Preparation</h2><span class="badge badge-sourced_unmodeled_substep">Observed state</span></div>
        <h3>Assumptions</h3>{list_items(list(starting.get("assumptions", [])))}
        {requirements_markup(requirements)}
      </section>
      <section class="section" id="checkpoints">
        <div class="section-heading"><h2>Checkpoints</h2><span class="badge badge-unresolved">Includes unresolved state</span></div>
        <ul class="checkpoints">{"".join(checkpoint_markup(item) for item in checkpoints if item)}</ul>
      </section>
      <section class="section" id="steps">
        <div class="section-heading"><h2>Steps</h2><span class="badge badge-unresolved">Manual confirmation</span></div>
        <ol class="steps">{main_steps}</ol>
      </section>
      {branch_markup}
      <section class="section" id="safety">
        <div class="section-heading"><h2>Safety and passive checks</h2><span class="badge badge-unresolved">Player judgment required</span></div>
        <h3>Current observations</h3>{list_items(list(safety.get("current_observations_required", [])))}
        <h3>Risk acceptance</h3>{list_items(list(safety.get("player_risk_requirements", [])))}
        <p class="boundary"><span>Survival boundary:</span> No death, escape, safe travel, or return is inferred.</p>
        <h3>Passive-check policy</h3><ul class="plain-list">{passive_markup}</ul>
      </section>
      <section class="section" id="stop-reentry">
        <div class="section-heading"><h2>Stop and re-entry</h2><span class="badge badge-unresolved">No completion inferred</span></div>
        <h3>Stop conditions</h3>{list_items(list(stops.get("stop_conditions", [])))}
        <h3>Re-entry conditions</h3>{list_items(list(stops.get("reentry_conditions", [])))}
      </section>
      <section class="section" id="sources">
        <div class="section-heading"><h2>Sources</h2><span class="badge badge-sourced_unmodeled_substep">Research evidence</span></div>
        <ul class="sources">{sources}</ul>
      </section>
      <footer class="reader-footer">This reader visualizes research evidence. It does not select a route, apply an action, claim items or GP, or infer completion, timing, combat success, travel, or safety.</footer>
    </article>
  </main>
  <script>
    (() => {{
      const storageKey = "osrs-progression-guide:{text(segment_id)}";
      const checks = [...document.querySelectorAll(".step-check")];
      const status = document.getElementById("storage-status");
      let saved = {{}};
      try {{ saved = JSON.parse(localStorage.getItem(storageKey) || "{{}}"); }} catch (_) {{ status.textContent = "Local step storage is unavailable in this browser."; }}
      checks.forEach((check) => {{
        check.checked = saved[check.dataset.stepId] === true;
        check.addEventListener("change", () => {{
          try {{
            const next = Object.fromEntries(checks.map((item) => [item.dataset.stepId, item.checked]));
            localStorage.setItem(storageKey, JSON.stringify(next));
          }} catch (_) {{ status.textContent = "Local step storage is unavailable in this browser."; }}
        }});
      }});
      document.getElementById("reset-checks").addEventListener("click", () => {{
        checks.forEach((check) => {{ check.checked = false; }});
        try {{ localStorage.removeItem(storageKey); }} catch (_) {{ status.textContent = "Local step storage is unavailable in this browser."; }}
      }});
    }})();
  </script>
</body>
</html>
"""


def render_file(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_segment(load_json(input_path)), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", default=DEFAULT_INPUT, help="Execution-segment JSON input")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Standalone HTML output")
    args = parser.parse_args(argv)
    render_file(args.input, args.output)
    print(f"Rendered {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
