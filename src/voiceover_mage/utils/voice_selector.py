# ABOUTME: Interactive voice selection UI for choosing voice previews from the terminal

import contextlib

from rich.console import Console
from rich.table import Table

from voiceover_mage.persistence.models import VoicePreview
from voiceover_mage.utils.audio_player import AudioPlayer


class VoiceSelector:
    """Interactive voice selection UI with audio preview support."""

    def __init__(self, console: Console | None = None):
        """Initialize the voice selector.

        Args:
            console: Rich console for output (creates new one if not provided)
        """
        self.console = console or Console()
        self.audio_player = AudioPlayer()

    def _create_choice_label(self, idx: int, preview: VoicePreview) -> str:
        """Create a formatted choice label for a voice preview.

        Args:
            idx: Index of the preview
            preview: Voice preview to format

        Returns:
            str: Formatted label string
        """
        # Truncate prompt if too long
        prompt_preview = preview.voice_prompt[:60] + "..." if len(preview.voice_prompt) > 60 else preview.voice_prompt

        # Format date
        date_str = preview.created_at.strftime("%Y-%m-%d")

        # Build label
        label = f"[{idx}] {prompt_preview} ({preview.provider}, {date_str})"

        if preview.is_representative:
            label += " ⭐ SELECTED"

        return label

    def display_voice_table(self, previews: list[VoicePreview], npc_name: str) -> None:
        """Display voice previews in a rich table.

        Args:
            previews: List of voice previews to display
            npc_name: Name of the NPC
        """
        table = Table(title=f"🎭 Voice Previews for {npc_name}", show_lines=True)

        table.add_column("#", style="cyan", no_wrap=True, justify="right")
        table.add_column("Voice Description", style="magenta")
        table.add_column("Sample Text", style="white")
        table.add_column("Provider", style="blue", no_wrap=True)
        table.add_column("Date", style="green", no_wrap=True)
        table.add_column("Selected", style="yellow", no_wrap=True, justify="center")

        for idx, preview in enumerate(previews):
            # Truncate text for display
            prompt_preview = (
                preview.voice_prompt[:50] + "..." if len(preview.voice_prompt) > 50 else preview.voice_prompt
            )
            sample_preview = preview.sample_text[:40] + "..." if len(preview.sample_text) > 40 else preview.sample_text
            date_str = preview.created_at.strftime("%Y-%m-%d")
            selected_mark = "⭐" if preview.is_representative else ""

            table.add_row(str(idx), prompt_preview, sample_preview, preview.provider, date_str, selected_mark)

        self.console.print(table)

    async def select_voice_interactive(self, previews: list[VoicePreview], npc_name: str) -> int | None:
        """Interactively select a voice preview with audio playback.

        Args:
            previews: List of voice previews to choose from
            npc_name: Name of the NPC

        Returns:
            int | None: Index of selected preview, or None if cancelled
        """
        if not previews:
            self.console.print("[red]No voice previews available[/red]")
            return None

        # Use prompt_toolkit directly for custom keybindings
        import subprocess
        import tempfile
        import threading
        from pathlib import Path

        from prompt_toolkit import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import FormattedTextControl, Window
        from prompt_toolkit.layout.dimension import Dimension as D
        from prompt_toolkit.layout.layout import Layout
        from prompt_toolkit.styles import Style
        from prompt_toolkit.widgets import Frame

        kb = KeyBindings()
        current_idx: dict[str, int] = {"value": 0}
        result: dict[str, int | None] = {"value": None}
        playing: dict[str, bool] = {"value": False}
        audio_process: dict[str, subprocess.Popen[bytes] | None] = {"value": None}

        # Custom style for the menu
        custom_style = Style.from_dict(
            {
                "selected": "bg:#673ab7 #ffffff bold",  # Purple background, white text
                "playing": "bg:#00c853 #ffffff bold blink",  # Green background, white text, blinking
                "normal": "#cccccc",  # Light gray
            }
        )

        def get_formatted_text():
            """Generate the current menu display with proper line breaks."""
            lines = []
            lines.append(("class:title", f"🎭 Voice Previews for {npc_name}\n"))
            lines.append(("", "\n"))

            for idx, preview in enumerate(previews):
                label = self._create_choice_label(idx, preview)

                # Determine the style and icon for this line
                if playing["value"] and idx == current_idx["value"]:
                    prefix = "🔊 "
                    style_class = "class:playing"
                elif idx == current_idx["value"]:
                    prefix = "⭐ "
                    style_class = "class:selected"
                else:
                    prefix = "  "
                    style_class = "class:normal"

                lines.append((style_class, f"{prefix}{label}"))
                lines.append(("", "\n"))

            lines.append(("", "\n"))
            if self.audio_player.can_play():
                lines.append(("class:help", "📍 ↑↓: navigate | Space: preview | Enter: select | x: cancel"))
            else:
                lines.append(("class:warning", "⚠️  Audio playback not available"))

            return lines

        def stop_audio():
            """Stop any currently playing audio."""
            if audio_process["value"]:
                try:
                    audio_process["value"].terminate()
                    audio_process["value"].wait(timeout=0.5)
                except (subprocess.TimeoutExpired, Exception):
                    with contextlib.suppress(Exception):
                        audio_process["value"].kill()
                audio_process["value"] = None
            playing["value"] = False

        def play_audio_background(idx: int, app):
            """Play audio in background thread."""
            audio_bytes = previews[idx].audio_bytes
            if not audio_bytes:
                return

            # Write audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = Path(tmp.name)

            # Start ffplay in background
            player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(tmp_path)]
            process = subprocess.Popen(player_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio_process["value"] = process

            # Wait for process to finish
            process.wait()

            # Cleanup
            with contextlib.suppress(Exception):
                tmp_path.unlink()

            # Clear playing state and refresh
            if audio_process["value"] == process:  # Only clear if we're still the current player
                audio_process["value"] = None
                playing["value"] = False
                app.invalidate()

        @kb.add("up")
        def move_up(event):
            stop_audio()
            if current_idx["value"] > 0:
                current_idx["value"] -= 1
                event.app.invalidate()

        @kb.add("down")
        def move_down(event):
            stop_audio()
            if current_idx["value"] < len(previews) - 1:
                current_idx["value"] += 1
                event.app.invalidate()

        @kb.add("enter")
        def select(event):
            stop_audio()
            result["value"] = current_idx["value"]
            event.app.exit()

        @kb.add("x")
        def cancel(event):
            stop_audio()
            result["value"] = None
            event.app.exit()

        @kb.add(" ")  # Space bar
        def preview(event):
            """Preview the currently selected voice."""
            if not self.audio_player.can_play():
                return

            idx = current_idx["value"]
            if not previews[idx].audio_bytes:
                return

            # Stop any currently playing audio
            if playing["value"]:
                stop_audio()
            else:
                # Start new playback
                playing["value"] = True
                event.app.invalidate()

                # Play in background thread
                thread = threading.Thread(target=play_audio_background, args=(idx, event.app), daemon=True)
                thread.start()

        # Create the layout
        text_control = FormattedTextControl(text=get_formatted_text)
        window = Window(content=text_control, height=D(preferred=len(previews) + 5))

        container = Frame(window, title="Voice Selection")

        layout = Layout(container)

        # Create application with full screen to avoid jumping
        try:
            app = Application(layout=layout, key_bindings=kb, style=custom_style, full_screen=True, mouse_support=False)

            # Run the application
            await app.run_async()

            # Cleanup any playing audio
            stop_audio()

            if result["value"] is None:
                self.console.print("\n[yellow]Selection cancelled[/yellow]")
                return None

            return result["value"]

        except KeyboardInterrupt:
            stop_audio()
            self.console.print("\n[yellow]Selection cancelled[/yellow]")
            return None

    def play_preview(self, preview: VoicePreview) -> bool:
        """Play a voice preview.

        Args:
            preview: Voice preview to play

        Returns:
            bool: True if playback succeeded
        """
        if not self.audio_player.can_play():
            self.console.print("[yellow]Audio playback not available[/yellow]")
            return False

        if not preview.audio_bytes:
            self.console.print("[red]No audio data available for this preview[/red]")
            return False

        self.console.print("[cyan]🔊 Playing audio...[/cyan]")
        success = self.audio_player.play(preview.audio_bytes, block=True)

        if success:
            self.console.print("[green]✓ Playback finished[/green]")
        else:
            self.console.print("[yellow]⚠️  Playback failed[/yellow]")

        return success
