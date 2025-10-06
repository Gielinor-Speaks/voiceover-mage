# ABOUTME: Audio playback utilities for previewing voice samples in the terminal

import contextlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from loguru import logger


class AudioPlayer:
    """Simple audio player for previewing voice samples in the terminal."""

    def __init__(self):
        """Initialize the audio player and detect available playback tools."""
        self.player_cmd = self._detect_player()

    def _detect_player(self) -> str | None:
        """Detect which audio player is available on the system.

        Returns:
            str | None: Command name for the player, or None if none found
        """
        # Try ffplay first (part of ffmpeg, widely available)
        if shutil.which("ffplay"):
            return "ffplay"

        # Try mpg123 (common on Linux)
        if shutil.which("mpg123"):
            return "mpg123"

        # Try aplay (Linux, WAV only)
        if shutil.which("aplay"):
            return "aplay"

        # Try afplay (macOS)
        if shutil.which("afplay"):
            return "afplay"

        logger.warning("No audio player found (tried: ffplay, mpg123, aplay, afplay)")
        return None

    def can_play(self) -> bool:
        """Check if audio playback is available.

        Returns:
            bool: True if a player is available
        """
        return self.player_cmd is not None

    def play(self, audio_bytes: bytes, block: bool = True) -> bool:
        """Play audio from bytes.

        Args:
            audio_bytes: Raw audio data (MP3, WAV, etc.)
            block: If True, wait for playback to finish

        Returns:
            bool: True if playback succeeded, False otherwise
        """
        if not self.player_cmd:
            logger.warning("Cannot play audio - no player available")
            return False

        # Write audio to temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        try:
            if self.player_cmd == "ffplay":
                # ffplay: hide video window, auto-exit, no stats
                cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(tmp_path)]
            elif self.player_cmd == "mpg123":
                # mpg123: quiet mode
                cmd = ["mpg123", "-q", str(tmp_path)]
            elif self.player_cmd == "aplay":
                # aplay: quiet mode (WAV only, but we'll try)
                cmd = ["aplay", "-q", str(tmp_path)]
            elif self.player_cmd == "afplay":
                # afplay: macOS player
                cmd = ["afplay", str(tmp_path)]
            else:
                logger.error(f"Unknown player command: {self.player_cmd}")
                return False

            if block:
                result = subprocess.run(cmd, capture_output=True)
                success = result.returncode == 0
                if not success:
                    logger.warning(f"Audio playback failed: {result.stderr.decode()[:100]}")
                return success
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            return False
        finally:
            # Clean up temp file
            with contextlib.suppress(Exception):
                tmp_path.unlink()
