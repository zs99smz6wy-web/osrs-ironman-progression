# Route Output Placeholder

No final route is generated at this stage. A future route must be derived from a declared account state and cite the factual nodes it relies on. Each major recommendation must state its hard requirements, strategic rationale, alternatives or bypasses, stop point, and passive or AFK companion options.

The bounded [decision episode contract](decision-episodes.md) records short sequences of explicit, player-confirmed completions and regenerates recommendation context between them. It is an audit and framework-testing tool, not automatic route generation.

## Execution Segment Previews

Research-only execution segments can be rendered as standalone local readers without running a web server:

```powershell
python scripts/render_execution_segment.py
```

The checked-in example is [post-tutorial-varrock-museum-proof.html](previews/post-tutorial-varrock-museum-proof.html). It reads from `research/execution-segments/post-tutorial-varrock-museum-proof.json`; checkbox state stays only in the browser's local storage and never updates the account model or research data. To render another segment, pass its JSON path and an explicit `--output` path.
