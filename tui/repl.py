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
TUI: line-oriented REPL (a.k.a. command shell).

The TUI is state-thin: it only reads input, dispatches, and formats.
All logic lives in BrowserState / PlaybackEngine / CommandRegistry.
"""

import sys
from dataclasses import dataclass
from typing import Optional

from ..core.browser_state import BrowserState
from ..core.playback import PlaybackEngine
from ..core.commands import CommandContext, CommandRegistry, build_default_registry


@dataclass
class Repl:
    browser: BrowserState
    playback: PlaybackEngine
    registry: Optional[CommandRegistry] = None

    def __post_init__(self):
        if self.registry is None:
            self.registry = build_default_registry()

    def run(self) -> None:
        ctx = CommandContext(
            browser=self.browser,
            playback=self.playback,
            registry=self.registry,
            out=sys.stdout,
        )
        banner = (
            "pbrAudioDAW TUI  —  type `help` for commands, `exit` to quit.\n"
        )
        self._print(banner)

        while True:
            try:
                prompt = f"{self.browser.pwd()}> "
                line = input(prompt)
            except EOFError:
                self._print("")
                break
            except KeyboardInterrupt:
                self._print("^C")
                continue

            try:
                cont = self.registry.dispatch(ctx, line)
            except Exception as e:  # belt-and-braces
                self._print(f"error: {e}")
                continue

            if not cont:
                break

        self.playback.stop()

    def _print(self, msg: str) -> None:
        print(msg, flush=True)
