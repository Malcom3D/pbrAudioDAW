# Copyright (C) 2025 Malcom3D <malcom3d.gpl@gmail.com>
#
# This file is part of pbrAudio.
#
# pbrAudio is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pbrAudio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pbrAudio.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Navigation state for the pbrAudioStorage tree.

The browser owns a *current path* expressed as a list of segments:

    []                                    → scene root
    ["objects"]                           → a collection
    ["objects", "rigidbody"]              → an engine
    ["objects", "rigidbody", "3"]         → an object
    ["objects", "rigidbody", "3", "body"] → a track
    ["objects", "rigidbody", "3", "body", "vertex_42"] → a signal

Segment matching for tracks/signals is by name, not not index. Path
resolution is delegated to the backend, which knows how to enumerate
children of every node via ``get_meta``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

from pbrAudioStorage import StorageEngine
from pbrAudioStorage.lib.audio_data_type import AudioDataType


_ROOT = []


@dataclass
class BrowserEntry:
       """One line in a directory listing."""
    name: str
    path: List[str]
    kind: str                      # "collection" | "engine" | "object" | "track" | "signal"
    meta: Optional[AudioDataType] = None
    extra: str = ""                # free-form annotation shown by ``ls -l``


class BrowserState:
    """
    Holds the current working path and offers directory-style commands.
    """

    def __init__(self, storage: StorageEngine):
        self.storage = storage
        self._backend = storage._backend
        self._history: List[List[str]] = []
        self._cwd: List[str] = []

    # ------------------------------------------------------------------
    @property
    def cwd(self) -> List[str]:
        return list(self._cwd)

    def cwd_str(self, sep: str = "/") -> str:
        return sep + sep.join(self._cwd) if self._cwd else "/"

    # ------------------------------------------------------------------
    def _resolve_kind(self, path: Sequence[str]) -> str:
        n = len(path)
        if n == 0:
            return "root"
        if n == 1:
            return "collection"
        if n == 2:
            return "engine"
        if n == 3:
            return "object"
        if n == 4:
            return "track"
        return "signal"

    # ------------------------------------------------------------------
    def _children(self, path: Sequence[str]) -> List[BrowserEntry]:
        """
        Enumerate children of ``path`` by asking the backend.

        - collections/engines/objects: real blosc2 children
        - tracks: signal names from track_meta.child_names
        - signals: signal_meta.child_names (rare but supported)
        """
        kind = self._resolve_kind(path)
        prefix = "/" + "/".join(str(s) for s in path) if path else "/"
        out: List[BrowserEntry] = []

        try:
            if kind in ("root", "collection", "engine", "object"):
                raw = self._backend.list(prefix)
                # blosc2.list() returns full descendant paths; keep the
                # immediate child of prefix.
                prefixes = set()
                for child in raw:
                    tail = child[len(prefix):].strip("/") if prefix != "/" else child.strip("/")
                    head = tail.split("/", 1)[0]
                    if not head or head in prefixes:
                        continue
                    prefixes.add(head)
                    child_kind = self._resolve_kind(list(path) + [head])
                    entry_meta: Optional[AudioDataType] = None
                    entry_extra = ""
                    try:
                        full = "/" + "/".join([str(s) for s in path] + [head])
                        entry_meta = self._backend.get_meta(full)
                        if entry_meta is not None:
                            entry_extra = f"{entry_meta.data_type} ({entry_meta.default_behavior})"
                    except Exception:
                        pass
                    out.append(BrowserEntry(name=head, path=list(path) + [head],
                                            kind=child_kind, meta=entry_meta,
                                            extra=entry_extra))
            elif kind == "track":
                track_meta = self._backend.get_meta(prefix)
                for idx, name in zip(track_meta.child_indices, track_meta.child_names):
                    child_path = list(path) + [str(name)]
                    sig_meta = None
                    try:
                        sig_meta = self._backend.get_meta(prefix, signal_idx=idx)
                    except Exception:
                        pass
                    out.append(BrowserEntry(
                        name=str(name), path=child_path, kind="signal",
                        meta=sig_meta,
                        extra=(sig_meta.data_type if sig_meta else ""),
                    ))
            elif kind == "signal":
                # Some chains produce signal-of-signals; ask the backend.
                # Fall back to empty.
                pass
        except Exception as e:
            # Not-a-node: pretend it's empty; the caller will show the error.
            self._last_error = str(e)

        out.sort(key=lambda e: (e.kind, e.name))
        return out

    # ------------------------------------------------------------------
    def ls(self, target: Optional[str] = None) -> List[BrowserEntry]:
        """`ls [path]` — list the target directory."""
        path = self._cwd if target is None else self._resolve_arg(target)
        if path is None:
            raise FileNotFoundError(f"Unknown path: {target!r}")
        return self._children(path)

    # ------------------------------------------------------------------
    def _resolve_arg(self, arg: str) -> Optional[List[str]]:
        """
        Resolve a user-provided path (may be relative, ``.``, ``..``,
        absolute, or ``-`` for previous directory).
        """
        if arg == "-":
            if not self._history:
                return None
            return self._._history[-1]

        base = [] if arg.startswith("/") else list(self._cwd)
        for seg in arg.split("/"):
            if seg in ("", "."):
                continue
            if seg == "..":
                if base:
                    base.pop()
                continue
            base.append(seg)
        return base

    # ------------------------------------------------------------------
    def cd(self, target: Optional[str] = None) -> List[str]:
        """
        `cd [path]` — change directory.

        With no argument, returns to root (``cd`` ~= ``cd /``).
        """
        if target is None or target.strip() == "":
            new_path = []
        else:
            new_path = self._resolve_arg(target)
            if new_path is None:
                raise FileNotFoundError(f"No such path:: {target!r}")

        # Validate: path must resolve to a listing (even an empty one).
        kind = self._resolve_kind(new_path)
        if kind == "signal":
            # signals are leaves
            raise IsADirectoryError(f"{'/'.join(new_path)} is a signal, not a directory")
        if kind == "track":
            # ensure track node exists
            prefix = "/" + "/".join(new_path)
            try:
                self._backend.get_meta(prefix)
            except Exception:
                raise FileNotFoundError(f"Track not found: {prefix}")

        self._history.append(self._cwd)
        self._cwd = new_path
        return new_path

    # ------------------------------------------------------------------
    def pwd(self) -> str:
        return self.cwd_str()

    # ------------------------------------------------------------------
    def parse_signal_path(self, arg: str) -> Tuple[str, str, int, str, Optional[str]]:
        """
        Given a user path (absolute or relative), return the
        ``(collection, engine, obj_idx, track_name, signal_name)`` tuple
        suitable for ``StorageEngine.read``.

        Resolution rules:
        - root / collection / engine / object level → error
        - track level → ``signal_name=None`` (concat all signals on the
          calling code)
        - signal level → ``signal_name=<name>``
        """
        path = self._resolve_arg(arg)
        if path is None:
            raise FileNotFoundError(f"No such path: {arg!r}")

        if len(path) < 3:
            raise ValueError(f"Path {arg!r} does not address an object or deeper")
        if len(path) > 5:
            raise ValueError(f"Path {arg!r} is deeper than a signal")

        collection = path[0]
        engine = path[1]
        obj_idx = int(path[2])
        track_name = path[3] if len(path) >= 4 else None
        signal_name = path[4] if len(path) >= 5 else None

        if track_name is None:
            raise ValueError(f"Path {arg!r} must reach at least a track")

        return collection, engine, obj_idx, track_name, signal_name
