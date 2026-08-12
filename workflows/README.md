# Workflow packs

Named, inspectable workflow definitions (tool allowlist + steps) that Arbora can turn into plans and promote to trusted routines.

## Layout

- Bundled packs: `workflows/*.json` in this repository
- User packs: `~/.arbora/workflows/*.json` (override by `id`)

## Format

```json
{
  "id": "list-downloads",
  "name": "List Downloads",
  "description": "Read-only listing of the Downloads folder.",
  "goal_phrases": ["list downloads", "show downloads"],
  "rationale": "Why this workflow exists.",
  "steps": [
    {
      "adapter": "files",
      "action": "list_directory",
      "args": { "path": "~/Downloads" },
      "summary": "List files in Downloads",
      "sensitivity": "read",
      "side_effects": ["Reads directory listing"]
    }
  ]
}
```

`sensitivity` must be one of: `read`, `mutate`, `destructive`, `credential`, `financial`.

## Use

```powershell
arbora --provider echo
/workflows
# goal matching a phrase, e.g. "list downloads"
# Approve & run, then Promote to trusted routine if desired
```

Packs are matched after built-in journey templates and before model/provider fallback.
