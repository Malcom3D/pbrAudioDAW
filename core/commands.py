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
REPL command registry and built-in commands.

Each command receives a `CommandContext` and the list of positional
arguments after the command name.
"""

import shlex
import sys
import traceback
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .browser_state import BrowserState
from .playback import PlaybackEngine

@dataclass
class CommandContext:
    browser: "BrowserState"
    playback: "PlaybackEngine"
    registry: "CommandRegistry"
    out: Optional[object] = None  # defaults to sys.stdout

    def __post_init__(self):
        if self.out is None:
            self.out = sys.stdout

    def echo(self, msg: str) -> None:
        print(msg, file=self.out)

CommandFn = Callable[[CommandContext, List[str]], None]

class CommandRegistry:
    def __init__(self):
        self._cmds: Dict[str, CommandFn] = {}
        self._help: Dict[str, str] = {}

    def register(self, name: str, help_text: str, fn: CommandFn):
        self._cmds[name] = fn
        self._help[name] = help_text

    def names(self) -> List[str]:
        return sorted(self._cmds)

    def help_text(self, name: str) -> str:
        return self._help.get(name, "")

    def dispatch(self, ctx: CommandContext, line: str) -> bool:
        """Return False to request REPL exit."""
        if not line.strip():
            return True
        if line.strip() in ("exit", "quit"):
            return False

        try:
            parts = shlex.split(line)
        except ValueError as e:
            ctx.echo(f"parse error: {e}")
            return True

        name, args = parts[0], parts[1:]
        fn = self._cmds.get(name)
        if fn is None:
            ctx.echo(f"unknown command: {name!r} (type `help` for a list)")
            return True

        try:
            fn(ctx, args)
        except Exception as e:
            ctx.echo(f"{name}: {e}")
            traceback.print_exc(file=ctx.out)
        return True

# ----------------------------------------------------------------------
# built-ins
# ----------------------------------------------------------------------

def _cmd_pwd(ctx: CommandContext, args: List[str]) -> None:
    ctx.echo(ctx.browser.pwd())


def _cmd_cd(ctx: CommandContext, args: List[str]) -> None:
    target = args[0] if args else None
    ctx.browser.cd(target)


def _cmd_ls(ctx: CommandContext, args: List[str]) -> None:
    """`ls [-l] [path]`"""
    long_fmt = False
    rest = list(args)
    if rest and rest[0] == "-l":
        long_fmt = True
        rest = rest[1:]
    target = rest[0] if rest else None

    entries = ctx.browser.ls(target)
    if not entries:
        return

    if long_fmt:
        width = max(len(e.name) for e in entries)
        for e in entries:
            ctx.echo(f"{e.kind:<12} {e.name:<{width}}  {e.extra}")
    else:
        for e in entries:
            suffix = "/" if e.kind in ("collection", "engine", "object", "track") else ""
            ctx.echo(f"{e.name}{suffix}")


def _cmd_play(ctx: CommandContext, args: List[str]) -> None:
    """`play <path>`"""
    if not args:
        raise ValueError("usage: play <path>")
    spec = ctx.browser.parse_signal_path(args[0])
    n = ctx.playback.prepare(spec, unprocessed=False)
    ctx.echo(f"playing {args[0]} ({n} samples)")
    ctx.playback.play_prepared()


def _cmd_stop(ctx: CommandContext, args: List[str]) -> None:
    ctx.playback.stop()


def _cmd_help(ctx: CommandContext, args: List[str]) -> None:
    if args:
        h = ctx.registry.help_text(args[0])
        ctx.echo(h or f"no help for {args[0]!r}")
        return
    for name in ctx.registry.names():
        ctx.echo(f"{name:<10} {ctx.registry.help_text(name)}")


def build_default_registry() -> CommandRegistry:
    reg = CommandRegistry()
    reg.register("pwd", "print working directory", _cmd_pwd)
    reg.register("ls", "ls [-l] [path]  — list directory contents", _cmd_ls)
    reg.register("cd", "cd [path]  — change directory ('..', '-', '/' supported)", _cmd_cd)
    reg.register("play", "play <path>  — stream a signal from pbrAudioStorage", _cmd_play)
    reg.register("stop", "stop the current playback", _cmd_stop)
    reg.register("help", "help [command]", _cmd_help)
    return reg
