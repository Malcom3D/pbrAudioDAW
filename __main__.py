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
CLI entry point:

    python -m pbrAudioDAW <scene_config.json>
"""

import argparse
import sys

from pbrAudioCommon import EntityManager
from pbrAudioStorage import StorageEngine

from .core.browser_state import BrowserState
from .core.playback import PlaybackEngine
from .tui.repl import Repl

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="pbrAudioDAW TUI")
    parser.add_argument("config", help="path to the pbrAudio scene config (json)")
    parser.add_argument("--backend", default=None, help="override storage backend ('blosc2' or 'zarr')")
    parser.add_argument("--urlpath", default=None, help="override storage urlpath (falls back to config)")
    parser.add_argument("--device", type=int, default=None, help="sounddevice output device index")
    parser.add_argument("--blocksize", type=int, default=1024, help="sounddevice stream blocksize")
    args = parser.parse_args(argv)

    entity_manager = EntityManager(args.config)
    storage = StorageEngine(entity_manager=entity_manager, backend=args.backend or "blosc2", urlpath=args.urlpath)

    browser = BrowserState(storage)
    playback = PlaybackEngine(storage=storage, device=args.device, blocksize=args.blocksize)

    Repl(browser=browser, playback=playback).run()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

