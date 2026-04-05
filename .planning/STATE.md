# Project State

**Project:** KohakuTerrarium
**Milestone:** v0.3.0
**Last activity:** 2026-04-05 - Completed target abstraction + launcher refactor (260405-r16)

### Current Phase
Phase 1-5a: kt studio foundation + target abstraction (complete)

### Completed
- 260405-nm0: kt studio subsystem -- config/profiles/launcher/CLI (43 tests, 738 lines)
- 260405-o7l: kt studio Phase 2 -- session management (32 tests, 854 lines)
- 260405-oks: kt studio Phase 3 -- statusline + themes (29 tests, ~600 lines)
- 260405-p5r: kt studio Phase 4 -- copilot CLI integration (21 tests, ~420 lines)

### Decisions
- Dataclasses over pydantic for studio config (matches core/config.py)
- Hooks append semantics (profile extends base, not replaces)
- Settings merge: env=dict-merge, hooks=extend, permissions=shallow-merge
- Standalone Python statusline runner (no KT imports, Claude Code invokes as external cmd)
- 6 built-in themes: dark, light, nord, tokyo-night, rose-pine, gruvbox
- Copilot config: JSON at ~/.copilot/config.json (matches Copilot CLI convention), env var COPILOT_MODEL takes priority
- Target ABC + registry pattern for multi-target support (claude-code, copilot, future)
- Base settings loading stays in ProfileLauncher to preserve test patch points

### Blockers/Concerns
None

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260405-nm0 | kt studio subsystem - config/profiles/launcher/CLI | 2026-04-05 | 0889390 | [260405-nm0-kt-studio](./quick/260405-nm0-kt-studio-subsystem-consolidate-tweakcc-/) |
| 260405-o7l | kt studio Phase 2 session management | 2026-04-05 | a76f67a | [260405-o7l](./quick/260405-o7l-kt-studio-phase-2-session-management-nam/) |
| 260405-oks | kt studio Phase 3 statusline + themes | 2026-04-05 | f236839 | [260405-oks](./quick/260405-oks-kt-studio-phase-3-statusline-themes-segm/) |
| 260405-p5r | kt studio Phase 4 copilot CLI integration | 2026-04-05 | 171e9f8 | [260405-p5r](./quick/260405-p5r-kt-studio-phase-4-copilot-cli-integratio/) |
| 260405-r16 | kt studio Phase 5a target abstraction + launcher refactor | 2026-04-05 | 4e9308a | [260405-r16](./quick/260405-r16-kt-studio-phase-5a-target-abstraction-la/) |
