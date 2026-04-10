"""Session management routes. List saved sessions and resume them."""

import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from kohakuterrarium.api.deps import get_manager
from kohakuterrarium.session.memory import SessionMemory
from kohakuterrarium.session.resume import (
    detect_session_type,
    resume_agent,
    resume_terrarium,
)
from kohakuterrarium.session.store import SessionStore

router = APIRouter()

_SESSION_DIR = Path.home() / ".kohakuterrarium" / "sessions"


# In-memory session index (built once, refreshed on demand)
_session_index: list[dict] = []
_index_built_at: float = 0


def _build_session_index() -> list[dict]:
    """Build index of all sessions. Cached in memory."""
    global _session_index, _index_built_at

    if not _SESSION_DIR.exists():
        _session_index = []
        return _session_index

    session_files = list(_SESSION_DIR.glob("*.kohakutr")) + list(
        _SESSION_DIR.glob("*.kt")
    )

    results = []
    for path in session_files:
        try:
            store = SessionStore(path)
            meta = store.load_meta()

            # Read first user message for preview
            preview = ""
            try:
                agent_name = (meta.get("agents") or [""])[0]
                if agent_name:
                    events = store.get_events(agent_name)
                    for evt in events:
                        if evt.get("type") == "user_input":
                            preview = (evt.get("content") or "")[:200]
                            break
            except Exception:
                pass

            store.close(update_status=False)

            results.append(
                {
                    "name": path.stem,
                    "filename": path.name,
                    "config_type": meta.get("config_type", "unknown"),
                    "config_path": meta.get("config_path", ""),
                    "terrarium_name": meta.get("terrarium_name", ""),
                    "agents": meta.get("agents", []),
                    "status": meta.get("status", ""),
                    "created_at": meta.get("created_at", ""),
                    "last_active": meta.get("last_active", ""),
                    "preview": preview,
                    "pwd": meta.get("pwd", ""),
                }
            )
        except Exception:
            results.append({"name": path.stem, "filename": path.name, "error": True})

    results.sort(
        key=lambda s: s.get("last_active") or s.get("created_at") or "",
        reverse=True,
    )

    _session_index = results
    _index_built_at = time.time()
    return results


def _get_session_index(max_age: float = 30.0) -> list[dict]:
    """Get cached session index, rebuild if stale."""
    if time.time() - _index_built_at > max_age:
        return _build_session_index()
    return _session_index


@router.get("")
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    search: str = "",
    refresh: bool = False,
):
    """List saved sessions with search and pagination.

    Args:
        limit: Max sessions to return (default 20)
        offset: Skip first N sessions (for pagination)
        search: Filter by name, config, agents, preview (case-insensitive)
        refresh: Force rebuild the session index
    """
    if refresh:
        _build_session_index()

    all_sessions = _get_session_index()

    # Server-side search
    if search:
        q = search.lower()
        all_sessions = [
            s
            for s in all_sessions
            if q
            in " ".join(
                [
                    s.get("name", ""),
                    s.get("config_path", ""),
                    s.get("config_type", ""),
                    s.get("terrarium_name", ""),
                    s.get("preview", ""),
                    s.get("pwd", ""),
                    " ".join(s.get("agents", [])),
                ]
            ).lower()
        ]

    total = len(all_sessions)
    page = all_sessions[offset : offset + limit]
    return {"sessions": page, "total": total, "offset": offset, "limit": limit}


@router.delete("/{session_name}")
async def delete_session(session_name: str):
    """Delete a saved session file."""
    path = None
    for ext in (".kohakutr", ".kt"):
        candidate = _SESSION_DIR / f"{session_name}{ext}"
        if candidate.exists():
            path = candidate
            break

    if path is None:
        # Prefix match
        matches = [
            p
            for p in list(_SESSION_DIR.glob("*.kohakutr"))
            + list(_SESSION_DIR.glob("*.kt"))
            if p.stem == session_name
        ]
        if len(matches) == 1:
            path = matches[0]

    if path is None:
        raise HTTPException(
            status_code=404, detail=f"Session not found: {session_name}"
        )

    try:
        path.unlink()
        return {"status": "deleted", "name": session_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")


@router.post("/{session_name}/resume")
async def resume_session(session_name: str):
    """Resume a saved session. Returns the created instance ID.

    The frontend can then connect to the instance via normal
    terrarium/agent WebSocket and history endpoints.
    """
    # Find the session file
    path = None
    for ext in (".kohakutr", ".kt"):
        candidate = _SESSION_DIR / f"{session_name}{ext}"
        if candidate.exists():
            path = candidate
            break

    if path is None:
        # Try prefix match
        matches = [
            p
            for p in list(_SESSION_DIR.glob("*.kohakutr"))
            + list(_SESSION_DIR.glob("*.kt"))
            if p.stem.startswith(session_name) or session_name in p.stem
        ]
        if len(matches) == 1:
            path = matches[0]
        elif len(matches) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Ambiguous session name, {len(matches)} matches. "
                f"Options: {[m.stem for m in matches[:5]]}",
            )

    if path is None:
        raise HTTPException(
            status_code=404, detail=f"Session not found: {session_name}"
        )

    session_type = detect_session_type(path)
    manager = get_manager()

    try:
        # Force CLI mode (headless) for web resume. TUI can't run without a TTY.
        if session_type == "terrarium":
            runtime, store = resume_terrarium(path, io_mode="cli")
            tid = await manager.register_terrarium(runtime, store)
            return {
                "instance_id": tid,
                "type": "terrarium",
                "session_name": path.stem,
            }
        else:
            agent, store = resume_agent(path, io_mode="cli")
            aid = await manager.register_agent(agent, store)
            return {
                "instance_id": aid,
                "type": "agent",
                "session_name": path.stem,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {e}")


def _resolve_session_path(session_name: str) -> Path | None:
    """Shared session file lookup (name, prefix, or full path)."""
    for ext in (".kohakutr", ".kt"):
        candidate = _SESSION_DIR / f"{session_name}{ext}"
        if candidate.exists():
            return candidate
    matches = [
        p
        for p in list(_SESSION_DIR.glob("*.kohakutr")) + list(_SESSION_DIR.glob("*.kt"))
        if p.stem == session_name
        or p.stem.startswith(session_name)
        or session_name in p.stem
    ]
    if len(matches) == 1:
        return matches[0]
    return None


@router.get("/{session_name}/memory/search")
async def search_session_memory(
    session_name: str,
    q: str,
    mode: str = "auto",
    k: int = 10,
    agent: str | None = None,
) -> dict[str, Any]:
    """Search a session's memory via FTS5 or semantic / hybrid modes.

    Read-only. Wraps the existing ``SessionMemory.search()`` — no new
    indexing behavior. Modes: ``auto`` (default), ``fts``, ``semantic``,
    ``hybrid``.
    """
    path = _resolve_session_path(session_name)
    if path is None:
        raise HTTPException(404, f"Session not found: {session_name}")

    try:
        # For running instances, use the live SessionStore from the manager
        # so we read fresh data (including unflushed WAL cache). For saved
        # sessions, open a read-only store from the file.
        manager = get_manager()
        live_store = None
        for sid, session in manager._agents.items():
            if hasattr(session, "agent") and hasattr(session.agent, "session_store"):
                ss = session.agent.session_store
                if ss and str(path) in str(getattr(ss, "_path", "")):
                    live_store = ss
                    break

        if live_store:
            # Running instance — use the live store's built-in FTS directly.
            # The store indexes text in FTS as events arrive (append_event).
            live_store.flush()
            raw_results = live_store.search(q, k=k)
            results = [
                {
                    "content": r.get("meta", {}).get("event_key", ""),
                    "round": 0,
                    "block": 0,
                    "agent": r.get("meta", {}).get("agent", ""),
                    "block_type": r.get("meta", {}).get("type", ""),
                    "score": r.get("score", 0),
                    "ts": 0,
                    "tool_name": "",
                    "channel": "",
                }
                for r in raw_results
            ]
            # Enrich: fetch the actual text for each result
            for res in results:
                event_key = res["content"]
                if event_key:
                    try:
                        evt = live_store.events[event_key]
                        res["content"] = (
                            evt.get("content")
                            or evt.get("output")
                            or evt.get("text")
                            or str(evt)[:500]
                        )
                        res["ts"] = evt.get("ts", 0)
                        res["block_type"] = evt.get("type", res["block_type"])
                    except (KeyError, Exception):
                        pass
        else:
            # Saved session — open store, use SessionMemory with indexing.
            store = SessionStore(path)
            meta = store.load_meta()
            agents_list = meta.get("agents", [])

            memory = SessionMemory(str(path))
            for agent_name in agents_list:
                events = store.get_events(agent_name)
                if events:
                    memory.index_events(agent_name, events)
            store.close(update_status=False)

            mem_results = memory.search(query=q, mode=mode, k=k, agent=agent)
            results = [
                {
                    "content": r.content,
                    "round": r.round_num,
                    "block": r.block_num,
                    "agent": r.agent,
                    "block_type": r.block_type,
                    "score": r.score,
                    "ts": r.ts,
                    "tool_name": r.tool_name,
                    "channel": r.channel,
                }
                for r in mem_results
            ]
    except Exception as e:
        raise HTTPException(500, f"Memory search failed: {e}")

    return {
        "session_name": path.stem,
        "query": q,
        "mode": mode,
        "k": k,
        "count": len(results),
        "results": results,
    }
