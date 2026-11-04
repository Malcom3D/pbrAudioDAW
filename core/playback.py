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
Playback via sounddevice.

The engine is intentionally simple for the first version:
  1. Resolve the path to a `(collection, engine, obj_idx, track_name, signal_name)`.
  2. Read the whole (possibly chain-processed) signal from the storage.
  3. Push it to `sd.OutputStream` in real time.

Any long-term path (chunked reads, ring buffers, seek, etc.) can be
added later without changing the public surface.
"""

import threading
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd

from pbrAudioStorage import StorageEngine

@dataclass
class PlaybackEngine:
    storage: StorageEngine
    device: Optional[int] = None
    blocksize: int = 1024
    dtype: str = "float32"
    sample_rate

    _stream: Optional[sd.OutputStream] = field(default=None, init=False, repr=False)
    _buffer: Optional[np.ndarray] = field(default=None, init=False, repr=False)
    _cursor: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _callback(self, outdata, frames, time_info, status):
        with self._lock:
            if self._buffer is None:
                outdata.fill(0)
                raise sd.CallbackStop
            S = self._buffer.shape[1]
            remaining = S - self._cursor
            if remaining <= 0:
                outdata.fill(0)
                raise sd.CallbackStop
            n = min(frames, remaining)
            chunk = self._buffer[:, self._cursor:self._cursor + n].T
            outdata[:n] = chunk
            if n < frames:
                outdata[n:] = 0
            self._cursor += n

    def prepare(self, spec: Tuple[str, str, int, str, Optional[str]], unprocessed: bool = False) -> int:
        col, eng, oidx, track, sig = spec
        data = self.storage.read(
            collection=col, engine=eng, obj_idx=oidx,
            track_name=track, signal_name=sig,
            unprocessed=unprocessed,
        )
        if data is None:
            raise ValueError(f"no audio for {spec!r}")
        data = np.ascontiguousarray(data, dtype=np.float32)
        if data.ndim == 1:
            data = data.reshape(1, -1)

        self.stop()

        self._buffer = data
        self._cursor = 0

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=data.shape[0],
            dtype=self.dtype,
            blocksize=self.blocksize,
            device=self.device,
            callback=self._callback,
        )
        return data.shape[1]

    def play_prepared(self, block: bool = True,
                      duration_seconds: Optional[float] = None) -> None:
        if self._stream is None or self._buffer is None:
            raise RuntimeError("call prepare() first")
        if duration_seconds is not None:
            max_samples = int(duration_seconds * self.storage.sample_rate)
            with self._lock:
                self._buffer = self._buffer[:, :max_samples]
        self._stream.start()
        if block:
            try:
                self._stream.wait()
            finally:
                self.stop()

    def play(self, spec, unprocessed: bool = False,
             block: bool = True,
             duration_seconds: Optional[float] = None) -> None:
        self.prepare(spec, unprocessed=unprocessed)
        self.play_prepared(block=block, duration_seconds=duration_seconds)

    def stop(self) -> None:
        with self._lock:
            stream = self._stream
            self._stream = None
            self._buffer = None
            self._cursor = 0
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
