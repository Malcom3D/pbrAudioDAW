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
pbrAudioDAW — a platform-independent TUI/GUI digital audio workstation
for the pbrAudio suite.

Public API
----------
- ``BrowserState``      : navigation over the pbrAudioStorage tree
- ``PlaybackEngine``    : sounddevice-backed player
- ``Repl``              : the line-oriented TUI
- ``__main__.run()``    : CLI entry point (also used by ``python -m pbrAudioDAW``)
"""

__version__ = "0.0.2"
__author__ = "Malcom3D"
__description__ = "TUI/GUI DAW for pbrAudioStorage"

from .core.browser_state import BrowserState, BrowserEntry
from .core.playback import PlaybackEngine
from .core.commands import CommandContext, CommandRegistry, build_default_registry
from .tui.repl import Repl

__all__ = [
    "BrowserState",
    "BrowserEntry",
    "PlaybackEngine",
    "CommandContext",
    "CommandRegistry",
    "build_default_registry",
    "Repl",
]

