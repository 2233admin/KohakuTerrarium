# Frontend layout guide

KohakuTerrarium's web dashboard uses a flexible zone-based layout system
inspired by Blender / DaVinci Resolve workspaces and Foobar2000's edit
mode. This guide covers the default presets, keyboard shortcuts, edit
mode, and pop-out windows.

## Core concepts

- **Zone** — a region of the window (left sidebar, main, right sidebar,
  drawer, status bar, etc.). Zones are fixed; what lives inside them is
  not.
- **Panel** — a single-responsibility surface (Chat, Files, Activity,
  State, Canvas, Debug, Settings, …). Every panel declares its preferred
  zones and an orientation class (`tall-narrow`, `tall-wide`, `short-wide`,
  `thin-strip`, `any`).
- **Preset** — a named full-screen layout: which zones are visible, which
  panels sit in which zones, what size each zone is. Switching presets is
  instant; the chat panel stays mounted (Teleport) so your scroll position
  and draft text are preserved.
- **Edit mode** — a Foobar2000-style state where panels gain a kebab menu
  so you can replace, close, or pop out. Layouts can be saved as new
  presets.

## Default presets

All shipped presets are available from the preset strip at the top of the
workspace shell or via keyboard shortcut. The active preset is highlighted.

| Shortcut | Preset         | Use for                                            |
|----------|----------------|----------------------------------------------------|
| Ctrl+1   | Chat focus     | Default for single-creature instances              |
| Ctrl+2   | Workspace      | Code work: Files, Editor, Chat side by side        |
| Ctrl+3   | Multi-creature | Default for terrarium instances                    |
| Ctrl+4   | Canvas         | Artifact-forward: Canvas in main, Chat on the side |
| Ctrl+5   | Debug          | Full debug drawer + Chat + State                   |
| Ctrl+6   | Settings       | Settings fills main as an escape hatch             |

The instance route (`/instances/:id`) picks a sensible default on first
open (`chat-focus` for creatures, `multi-creature` for terrariums) and
remembers your last choice per instance in `localStorage`.

## Keyboard shortcuts

| Shortcut       | Action                                                   |
|----------------|----------------------------------------------------------|
| Ctrl+1..6      | Switch to the matching preset                            |
| Ctrl+Shift+L   | Toggle layout edit mode                                  |
| Ctrl+K         | Open the command palette                                 |
| Esc            | Close edit mode (prompts if there are unsaved changes)   |

`Ctrl+K` always wins even when an input is focused. The preset-switch
shortcuts are ignored inside text inputs and textareas.

## Command palette

Open with Ctrl+K. Start typing and the palette fuzzy-matches against
every registered command. Prefixes route the query:

- `>` — commands (default when no prefix)
- `@` — mentions / files / blocks (reserved for later phases)
- `#` — sessions (reserved)
- `/` — slash commands (`/clear`, `/model`, `/status`, `/compact`)

Built-in commands include:

- `Mode: <preset>` — switch to any preset.
- `Panel: <panel>` — add a panel to its preferred zone.
- `Layout: enter edit mode` / `save current as new preset` / `reset`.
- `Debug: open logs tab` — quick debug jump.

Panels can register their own commands by calling
`paletteStore.register(...)` at mount time.

## Edit mode

Press **Ctrl+Shift+L** (or click the pencil button in the preset strip)
to enter edit mode. The workspace picks up an amber banner at the top
with `Save / Save as new / Revert / Exit` buttons. Each panel gains a
kebab menu with:

- **Replace…** — opens a picker modal listing every registered panel.
- **Close** — removes the panel from its slot.
- **Pop out** — opens the panel in its own window.

Orientation warnings (`⚠ prefers <zone>`) appear when a panel is placed
somewhere that doesn't match its declared orientation class. Placement
is never blocked — the warning is informational.

**Saving:** built-in presets can't be overwritten. To keep your changes,
click `Save as new`, give the layout a name and an optional shortcut,
and your preset becomes the active one. User presets are stored under
`kt.presets.user` in `localStorage`.

**Revert** restores the active preset to its pre-edit state. **Exit**
(or Esc) leaves edit mode; if you have unsaved changes it will ask for
confirmation first.

## Canvas preset + artifact detection

Canvas automatically collects two kinds of content from assistant
messages:

1. Explicit markers: `##canvas name=my-file lang=py## … ##canvas##`.
2. Fenced code blocks of at least 15 lines.

Each artifact gets a tab in the Canvas panel. Regenerating the same
source produces a new version (v1, v2, …) under the same tab. The
Canvas panel renders code / markdown / HTML today; SVG, mermaid, and
CSV viewers are on the roadmap.

First-artifact notifications appear in the toast center, but canvas
does not steal focus automatically — switch to the `canvas` preset
manually when you want to look at it.

## Debug panel

Open via Ctrl+5 or the `debug` command. Four tabs:

- **Logs** — live tail of the current API server process's log file
  over `/ws/logs`. Filter by level + text. Auto-scrolls.
- **Trace** — client-side waterfall of tool-call timings for the
  current tab.
- **Prompt** — on-demand fetch of `/agents/<id>/system-prompt` with
  Refresh, Copy, and a line-based Diff toggle that compares against
  the previous fetch.
- **Events** — firehose of every message in the chat store with a type
  filter and per-row JSON expand.

The only auto-open rule that steals focus is `processing_error`: a
system-role error in the active tab flips to the `debug` preset and
pops a toast.

## Detach to window

Any panel with `supportsDetach: true` can be popped out from the edit-
mode kebab. The detached window is a minimal single-panel shell that
talks to the backend independently (new websocket, new pinia instance).
Press **Reattach** in the popup to close it; the panel can be re-added
via the command palette.

Not every panel detaches well: the status bar and editor-status are
pinned to the main window on purpose.

## Settings

Open with Ctrl+6 or the `Mode: Settings` command. Seven read-only tabs:

- **Model** — current model + profile details + embedded model switcher.
- **Plugins** — list from `GET /agents/<id>/plugins`.
- **Extensions** — installed packages from `GET /api/registry`.
- **Triggers** — active triggers from `GET /agents/<id>/triggers`.
- **Cost** — session token totals, multiplied by a small shipped price
  table for the common GPT/Claude/o1 families.
- **Environment** — cwd + redacted env vars from `GET /agents/<id>/env`
  (server-side filter for credential-like keys).
- **Auto-open** — placeholder for the auto-trigger configuration UI.

## Troubleshooting

- **"no such panel" placeholder** — the active preset references a
  panel id that isn't registered. This happens temporarily when you
  switch to a preset for a feature from a later phase. Either pick a
  different preset or wait for the panel to land.
- **Chat doesn't render after preset switch** — the Teleport target
  should move the chat. If the shell detaches the mount unexpectedly,
  reload once; the WS + messages live in the chat store and survive.
- **Edit mode won't save** — built-in presets can't be overwritten;
  use Save as new.
- **Narrow windows** — below 900 px the shell auto-collapses side
  zones and keeps just main + status bar. Use the preset strip or
  the command palette to open other panels one at a time.
