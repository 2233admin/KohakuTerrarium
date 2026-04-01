In-Function Import Analysis
===========================

Comprehensive audit of every in-function import in `src/kohakuterrarium/`.
Produced 2026-04-01.

Methodology: each indented `import` / `from ... import` was located, its
surrounding context read, and both sides of any potential circular
dependency traced to determine whether the in-function placement is
justified.


========================================================================
1. TYPE_CHECKING Blocks (Standard Pattern -- All Fine)
========================================================================

These are imports guarded by `if TYPE_CHECKING:`. They only exist for
static analysis and never execute at runtime.  This is the canonical
Python pattern; no action needed.

File                                   | Line | Import
---------------------------------------|------|-----------------------------------------------
core/agent.py                          |   31 | core.environment.Environment
core/controller.py                     |   18 | llm.base.ToolSchema
core/controller.py                     |   19 | llm.message.ContentPart
core/events.py                         |   19 | llm.message.ContentPart, TextPart
terrarium/api.py                       |   17 | terrarium.observer.ChannelObserver
terrarium/api.py                       |   18 | terrarium.runtime.TerrariumRuntime
modules/tool/base.py                   |   15 | llm.message.ContentPart, ImagePart, TextPart
commands/read.py                       |   20 | core.controller.ControllerContext
prompt/plugins.py                      |   19 | core.registry.Registry
builtins/tools/registry.py             |   13 | modules.tool.base.BaseTool

Verdict: FINE.  No changes required.


========================================================================
2. Docstring / Comment-Only Imports (Inside Docstrings)
========================================================================

These appear inside module docstring `Usage:` blocks.  They are not
executed code; they are documentation examples.

File                                        | Line | Import
--------------------------------------------|------|----------------------------------------------
modules/subagent/__init__.py                |   16 | modules.subagent (usage example in docstring)
modules/trigger/__init__.py                 |   11 | modules.trigger (usage example in docstring)
builtins/subagents/__init__.py              |   17 | builtins.subagents (usage example in docstring)
core/session.py                             |    8 | core.session (usage example in docstring)
utils/logging.py                            |  168 | utils.logging (usage example in docstring)

Verdict: FINE.  These are not real imports.


========================================================================
3. Optional / Heavy Dependency Guards
========================================================================

These defer imports because the dependency is optional (not in core
`dependencies`) or extremely heavy (torch, whisper).

------------------------------------------------------------------------
3a. builtins/inputs/whisper.py -- torch, whisper
------------------------------------------------------------------------

  Line 115:  import torch           (inside _load_models)
  Line 166:  import torch           (inside _recording_loop)
  Line 245:  import torch           (inside _detect_speech)
  Line 269:  import whisper         (inside _process_audio)

Why: `torch` and `openai-whisper` are in [project.optional-dependencies]
under `asr`.  They are multi-GB packages.  Importing at top level would
force every user to install them even if they never use ASR.

The whole `whisper.py` module is already conditionally imported in
`builtins/inputs/__init__.py` (line 92, inside try/except ImportError).

Could these move to top level of whisper.py?  YES -- since the entire
module is already guarded by the conditional import in `__init__.py`,
anyone who reaches this module has torch/whisper installed.

Recommendation: Move `import torch` and `import whisper` to the top of
`builtins/inputs/whisper.py`.  The guard in `__init__.py` already
prevents import failures for users without the `asr` extra.

------------------------------------------------------------------------
3b. builtins/inputs/__init__.py -- WhisperASR
------------------------------------------------------------------------

  Line 92:  from builtins.inputs.whisper import WhisperASR, create_whisper_asr
            (inside try/except ImportError)

Why: Standard optional-dependency guard.  Correct pattern.

Verdict: FINE as-is.

------------------------------------------------------------------------
3c. llm/codex_provider.py -- openai.OpenAI
------------------------------------------------------------------------

  Line 82:  from openai import OpenAI    (inside _rebuild_client)

Why: `openai` IS a core dependency (listed in pyproject.toml).  There is
no circular chain: llm/codex_provider.py does not import from core/,
and nothing imports back to it circularly.

Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
3d. core/config.py -- yaml, json, tomllib
------------------------------------------------------------------------

  Line 201:  import yaml         (inside _load_yaml)
  Line 209:  import json         (inside _load_json)
  Line 218:  import tomllib      (inside _load_toml)
  Line 220:  import tomli        (inside _load_toml, fallback)

Why:
  - `yaml` (pyyaml) -- core dependency.  No reason to defer.
  - `json` -- stdlib.  No reason to defer.
  - `tomllib` -- stdlib (3.11+) with `tomli` fallback for 3.10.

The tomllib/tomli pattern is correct as a compatibility guard, but yaml
and json should be top-level.

Verdict:
  - `import yaml` -- UNNECESSARY.  Move to top level.
  - `import json` -- UNNECESSARY.  Move to top level.
  - tomllib/tomli try/except -- FINE structurally, but should be at module
    top level (the try/except pattern works at top level too).


========================================================================
4. Circular Import Avoidance (Verified)
========================================================================

------------------------------------------------------------------------
4a. core/scratchpad.py:93 -- core.session.get_session
------------------------------------------------------------------------

  Function: get_scratchpad()
  Import:   from kohakuterrarium.core.session import get_session

  Comment says: "session.py imports Scratchpad from this module"

  Verified chain:
    scratchpad.py  <--  session.py (line 23: from core.scratchpad import Scratchpad)
    session.py     <--  scratchpad.py (line 93: from core.session import get_session)

  This IS a real bidirectional dependency:
    session.py needs Scratchpad (to hold one as an attribute)
    scratchpad.py needs get_session() (convenience function)

  Verdict: LEGITIMATE circular avoidance.

  Fix options:
    a) Move get_scratchpad() to session.py (it already has Scratchpad).
       Remove the function from scratchpad.py entirely.  This is the
       cleanest fix -- the convenience function belongs with session.
    b) Accept the in-function import (it runs only when called, not at
       import time, so the cost is negligible).

------------------------------------------------------------------------
4b. core/channel.py:380 -- core.session.get_session
------------------------------------------------------------------------

  Function: get_channel_registry()
  Import:   from kohakuterrarium.core.session import get_session

  Comment says: "session.py imports ChannelRegistry from this module"

  Verified chain:
    channel.py  <--  session.py (line 22: from core.channel import ChannelRegistry)
    session.py  <--  channel.py (line 380: from core.session import get_session)

  Same pattern as 4a.

  Verdict: LEGITIMATE circular avoidance.

  Fix options:
    a) Move get_channel_registry() to session.py.  Same reasoning.
    b) Accept in-function import.

------------------------------------------------------------------------
4c. core/__init__.py:104 -- core.agent.Agent, run_agent
------------------------------------------------------------------------

  Pattern: Module-level __getattr__ lazy loading.
  Import:  from kohakuterrarium.core.agent import Agent, run_agent

  Comment says: "Lazy imports for modules that would cause circular
  import chains."

  Verified chain:
    core/__init__.py  imports at top level:
      core.config, core.conversation, core.controller, core.environment,
      core.events, core.executor, core.job, core.loader, core.registry

    core.agent imports:
      core.agent_handlers -> core.controller (already in __init__)
      core.agent_init -> core.controller (already in __init__)
                       -> core.config (already in __init__)
                       -> builtins.inputs -> various
                       -> builtins.outputs -> various
                       -> builtins.tools -> builtins.tools.registry -> (OK)
                       -> modules.trigger -> (OK)
                       -> prompt.aggregator -> parsing.format, core.registry (OK)
      core.config (already in __init__)
      core.events (already in __init__)
      core.loader (already in __init__)
      core.session -> core.channel, core.scratchpad (OK)
      core.termination -> (OK)
      core.trigger_manager -> (OK)
      modules.input.base -> core.events (already loaded)
      modules.output.base -> (OK)
      modules.trigger.base -> core.events (already loaded)
      session.output -> (OK)

    The real question: does anything imported by core/__init__.py at
    top level transitively need core.agent?

    core.controller -> NO (imports core.conversation, core.events, etc.)
    core.environment -> core.session -> core.channel, core.scratchpad -> NO
    core.executor -> core.events, core.job -> NO

    HOWEVER: core.__init__.py eagerly imports core.controller, which
    imports commands.read, which imports commands.base.  And
    core.agent_init imports from builtins.* which may trigger side
    effects.

    The fundamental issue is that Python's __init__.py is still being
    parsed when core.agent tries to import from sibling modules.
    If core/__init__.py imported core.agent at module level, and
    core.agent imported core.config (also in __init__), it would work
    because Python handles intra-package partial initialization -- BUT
    only if core.config is imported BEFORE core.agent in __init__.py.

    Actually, since nobody does `from kohakuterrarium.core import Agent`
    (verified: no such import exists in the codebase), and everyone
    imports `from kohakuterrarium.core.agent import Agent` directly,
    the __getattr__ lazy load is defensive but never actually triggered
    by normal code paths.

  Verdict: DEFENSIVE / POSSIBLY UNNECESSARY.  The lazy load is safe
  and has zero cost, but may no longer be needed since nobody imports
  Agent from the package __init__.  Could be simplified by removing
  Agent from __all__ and the __getattr__, but low priority.

------------------------------------------------------------------------
4d. core/agent_init.py:174-175 -- builtins.subagents, modules.subagent
------------------------------------------------------------------------

  Function: _init_subagents()
  Import:   from builtins.subagents import get_builtin_subagent_config
            from modules.subagent import SubAgentManager

  Comment says: "Import here to avoid circular imports
  (subagent -> core/conversation -> core/__init__ -> agent)"

  Verified: The claimed chain does NOT exist.
    modules.subagent.manager imports:
      core.events, core.job, core.registry (direct, not via core/__init__)
      llm.base
      modules.subagent.base -> core.conversation (direct)
      parsing.events

    core.conversation imports:
      llm.message (no cycle back to core.agent)

    builtins.subagents imports:
      modules.subagent.config (no cycle back to core.agent)

    Neither modules.subagent nor builtins.subagents import from
    core.agent or core.agent_init or core.__init__ at any depth.

  Verdict: UNNECESSARY.  The circular chain documented in the comment
  appears to have been broken by refactoring (everything now imports
  from specific core submodules, not from core/__init__).  These
  can be moved to top level.

------------------------------------------------------------------------
4e. core/agent_init.py:211 -- modules.subagent.config.SubAgentConfig
------------------------------------------------------------------------

  Function: _create_subagent_config()
  Import:   from modules.subagent.config import SubAgentConfig

  Same reasoning as 4d.  modules.subagent.config has NO internal
  KohakuTerrarium imports at all (only stdlib dataclass/enum/pathlib).

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
4f. core/agent_init.py:264 -- parsing.format
------------------------------------------------------------------------

  Function: _resolve_tool_format()
  Import:   from parsing.format import BRACKET_FORMAT, XML_FORMAT, ToolCallFormat

  Verified: parsing.format has NO KohakuTerrarium imports (only stdlib
  dataclass).  No circular dependency possible.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
4g. builtins/tools/registry.py:56 -- builtins.tools.terrarium_tools
------------------------------------------------------------------------

  Function: _ensure_terrarium_tools()
  Import:   import kohakuterrarium.builtins.tools.terrarium_tools

  Comment says: "avoids circular import at init"

  Verified chain:
    builtins.tools.__init__ imports builtins.tools.registry (line 7)
    builtins.tools.__init__ imports ALL tool modules (bash, edit, etc.)
    builtins.tools.terrarium_tools imports:
      builtins.tools.registry.register_builtin (would be circular if
        terrarium_tools were imported in __init__.py)
      terrarium.config, terrarium.tool_manager

    IF terrarium_tools were imported in builtins/tools/__init__.py:
      __init__.py -> terrarium_tools -> registry.register_builtin
      This would be fine because registry.py is imported first.

    But the deferred load here is NOT about __init__.py.  It's about
    registry.py itself: if registry.py imported terrarium_tools at
    top level, and terrarium_tools imports registry.register_builtin,
    we'd get:
      registry.py (loading) -> terrarium_tools -> registry.register_builtin
      (registry not yet fully initialized) -> AttributeError

    This is a real initialization-order issue.

  Verdict: LEGITIMATE.  The terrarium_tools module uses
  registry.register_builtin, so registry.py cannot import
  terrarium_tools at its own top level.

  Fix: Move the terrarium_tools import to builtins/tools/__init__.py
  (after the registry import).  This is the natural place since
  __init__.py already imports all other tool modules.  Then remove
  the _ensure_terrarium_tools() mechanism.

------------------------------------------------------------------------
4h. terrarium/runtime.py:374 -- builtins.tools.registry.get_builtin_tool
------------------------------------------------------------------------

  Function: _force_register_terrarium_tools()
  Import:   from builtins.tools.registry import get_builtin_tool

  Verified: builtins.tools.registry does NOT import from terrarium/.
  terrarium.runtime does NOT import from builtins.tools at top level.
  builtins.tools.terrarium_tools imports terrarium.config and
  terrarium.tool_manager, but NOT terrarium.runtime.

  No circular dependency exists.

  Verdict: UNNECESSARY.  Move to top level.


========================================================================
5. Unnecessary In-Function Imports (No Circular Dependency, Just Lazy)
========================================================================

These have no circular dependency and use modules that are always
available.  They should be moved to top level per project conventions.

------------------------------------------------------------------------
5a. core/controller.py:200 -- parsing.format
------------------------------------------------------------------------

  Function: _get_parser()
  Import:   from parsing.format import BRACKET_FORMAT, XML_FORMAT

  parsing.format has zero internal imports.  controller.py does not
  appear in parsing's import chain.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5b. core/controller.py:227 -- llm.tools
------------------------------------------------------------------------

  Function: _get_native_tool_schemas()
  Import:   from llm.tools import build_tool_schemas

  llm.tools imports core.registry and llm.base.  Neither imports
  core.controller.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5c. core/controller.py:302 -- llm.message (ContentPart, ImagePart, TextPart)
------------------------------------------------------------------------

  Function: _format_events_for_context()
  Import:   from llm.message import ContentPart, ImagePart, TextPart

  llm.message has zero internal imports.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5d. core/controller.py:358 -- llm.message (ContentPart, ImagePart, TextPart)
------------------------------------------------------------------------

  Function: run_once()
  Import:   from llm.message import ContentPart, ImagePart, TextPart

  Same as 5c -- duplicate.  Both should become one top-level import.

  Verdict: UNNECESSARY.  Merge with 5c into single top-level import.

------------------------------------------------------------------------
5e. core/events.py:82 -- llm.message.TextPart
------------------------------------------------------------------------

  Function: TriggerEvent.get_text_content()
  Import:   from llm.message import TextPart

  llm.message has zero internal imports.  Already imported under
  TYPE_CHECKING on line 19.

  Verdict: UNNECESSARY.  Move to top level (or use
  `from __future__ import annotations` and rely on TYPE_CHECKING).
  NOTE: The runtime isinstance() check on line 85 requires the actual
  class at runtime, not just the annotation.  So this MUST be a real
  import, not just TYPE_CHECKING.  Move to top level.

------------------------------------------------------------------------
5f. modules/tool/base.py:103 -- llm.message.TextPart
------------------------------------------------------------------------

  Function: ToolResult.get_text_output()
  Import:   from llm.message import TextPart

  Same pattern as 5e.  Used for isinstance() check.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5g. modules/tool/base.py:113 -- llm.message.ImagePart
------------------------------------------------------------------------

  Function: ToolResult.has_images()
  Import:   from llm.message import ImagePart

  Same pattern.  isinstance() check.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5h. prompt/plugins.py:142 -- parsing.format
------------------------------------------------------------------------

  Function: ToolUsagePlugin.render()
  Import:   from parsing.format import BRACKET_FORMAT, XML_FORMAT,
            format_tool_call_example

  parsing.format has zero internal imports.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5i. commands/read.py:259 -- asyncio
------------------------------------------------------------------------

  Function: WaitCommand._execute()
  Import:   import asyncio

  asyncio is stdlib.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5j. builtins/inputs/asr.py:261 -- asyncio
------------------------------------------------------------------------

  Function: DummyASR._transcribe()
  Import:   import asyncio

  asyncio is stdlib.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5k. builtins/inputs/cli.py:169 -- select
------------------------------------------------------------------------

  Function: CLIInput._try_read()
  Import:   import select

  select is stdlib.  Used conditionally (Unix only), but importing it
  on Windows does not fail -- it just has limited functionality.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5l. builtins/outputs/tts.py:310 -- asyncio
------------------------------------------------------------------------

  Function: DummyTTS._synthesize()
  Import:   import asyncio

  stdlib.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5m. builtins/outputs/tts.py:368-369 -- asyncio, sys
------------------------------------------------------------------------

  Function: ConsoleTTS._play_audio()
  Import:   import asyncio; import sys

  stdlib.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5n. builtins/outputs/tts.py:382 -- sys
------------------------------------------------------------------------

  Function: ConsoleTTS._stop_playback()
  Import:   import sys

  stdlib.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5o. serving/manager.py:174 -- core.environment.Environment
------------------------------------------------------------------------

  Function: KohakuManager.terrarium_create()
  Import:   from core.environment import Environment

  Verified: core.environment does NOT import from serving/.  No cycle.

  Verdict: UNNECESSARY.  Move to top level.

------------------------------------------------------------------------
5p. core/agent.py:31 -- core.environment.Environment (TYPE_CHECKING)
------------------------------------------------------------------------

  Already listed in section 1.  However, this means agent.py does not
  have Environment available at runtime.  If it needs it at runtime,
  the TYPE_CHECKING guard is wrong.  If it only uses it in annotations,
  the guard is correct (agent.py has `from __future__ import annotations`).

  Verdict: FINE (used only in type annotations, __future__ annotations
  is active).

------------------------------------------------------------------------
5q. llm/codex_provider.py:82 -- openai.OpenAI
------------------------------------------------------------------------

  See section 3c above.

  Verdict: UNNECESSARY.  Move to top level.


========================================================================
6. Summary Table
========================================================================

 #  | Category              | Count | Action
----|-----------------------|-------|--------------------------------------
 1  | TYPE_CHECKING         |    10 | None needed
 2  | Docstring examples    |     5 | None needed (not real code)
 3a | Optional dep (torch)  |     4 | Move to top of whisper.py
 3b | Optional dep guard    |     1 | Fine as-is
 3c | Unnecessary (openai)  |     1 | Move to top level
 3d | Unnecessary (yaml..)  |     3 | Move to top level
 4a | Circular (scratchpad) |     1 | Move function to session.py
 4b | Circular (channel)    |     1 | Move function to session.py
 4c | Defensive (__init__)  |     1 | Low priority; could remove
 4d | Stale comment         |     2 | Move to top level
 4e | Stale comment         |     1 | Move to top level
 4f | Stale comment         |     1 | Move to top level
 4g | Init-order (registry) |     1 | Move import to __init__.py
 4h | Unnecessary           |     1 | Move to top level
 5  | Unnecessary (lazy)    |    15 | Move to top level

Total in-function imports (excluding TYPE_CHECKING and docstrings): 32
  - Legitimate/fine as-is: 3  (4a, 4b, 4g -- though all have clean fixes)
  - Unnecessary / trivially fixable: 29


========================================================================
7. Recommended Fixes (Priority Order)
========================================================================

HIGH -- Stdlib / core dependency in-function imports (trivial, no risk):
  - core/controller.py: consolidate 4 in-function imports to top level
    (parsing.format, llm.tools, llm.message)
  - core/events.py: move llm.message.TextPart to top level
  - modules/tool/base.py: move llm.message.TextPart, ImagePart to top level
  - core/config.py: move yaml, json to top level; move tomllib/tomli
    try/except to top level
  - core/agent_init.py: move all 4 in-function imports to top level
  - prompt/plugins.py: move parsing.format to top level
  - commands/read.py: move asyncio to top level
  - builtins/outputs/tts.py: move asyncio, sys to top level
  - builtins/inputs/asr.py: move asyncio to top level
  - builtins/inputs/cli.py: move select to top level
  - serving/manager.py: move core.environment.Environment to top level
  - terrarium/runtime.py: move builtins.tools.registry to top level
  - llm/codex_provider.py: move openai to top level

MEDIUM -- Optional dependency restructuring:
  - builtins/inputs/whisper.py: move torch, whisper to top level
    (safe because the module is already conditionally imported)

LOW -- Circular dependency cleanup:
  - Move get_scratchpad() from core/scratchpad.py to core/session.py
  - Move get_channel_registry() from core/channel.py to core/session.py
  - Move terrarium_tools import from registry._ensure_terrarium_tools()
    to builtins/tools/__init__.py
  - Consider removing the __getattr__ lazy load in core/__init__.py


========================================================================
8. Circular Dependency Map
========================================================================

Only two real circular dependencies exist in the codebase:

  Chain 1:
    core/session.py  --imports-->  core/scratchpad.Scratchpad
    core/scratchpad.py  --imports (in-function)-->  core/session.get_session

  Chain 2:
    core/session.py  --imports-->  core/channel.ChannelRegistry
    core/channel.py  --imports (in-function)-->  core/session.get_session

Both follow the same pattern: session.py aggregates component types
(Scratchpad, ChannelRegistry) as attributes, and those components have
convenience functions that reach back to session for the "default"
instance.

Clean fix for both: move the convenience functions (get_scratchpad,
get_channel_registry) into session.py.  They conceptually belong there
since they operate on session state.  This eliminates both cycles.

  Chain 3 (init-order, not import cycle):
    builtins/tools/registry.py defines register_builtin()
    builtins/tools/terrarium_tools.py uses register_builtin()
    registry.py lazily loads terrarium_tools to avoid calling
      register_builtin before it is defined

  Fix: import terrarium_tools in builtins/tools/__init__.py after
  registry, alongside all other tool imports.
