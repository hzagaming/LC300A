import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SESSION_SOUND = PROJECT_ROOT / "distro/overlays/usr/libexec/lc300a/session-sound"


class SessionSoundTest(unittest.TestCase):
    def command(self, directory: Path, name: str, content: str) -> None:
        path = directory / name
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        path.chmod(0o755)

    def run_session_sound(self, directory: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = f"{directory}:/usr/bin:/bin"
        environment["LC300A_AUDIO_TEST_STATE"] = str(directory)
        return subprocess.run(
            ["/bin/sh", str(SESSION_SOUND)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_retries_until_audio_sink_is_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.command(
                directory,
                "wpctl",
                """
                #!/bin/sh
                calls_file=$LC300A_AUDIO_TEST_STATE/wpctl-calls
                calls=0
                test ! -f "$calls_file" || calls=$(cat "$calls_file")
                calls=$((calls + 1))
                printf '%s\n' "$calls" >"$calls_file"
                test "$calls" -ge 3 || exit 1
                printf 'Volume: 0.40\n'
                """,
            )
            self.command(
                directory,
                "pw-play",
                """
                #!/bin/sh
                printf '%s\n' "$*" >"$LC300A_AUDIO_TEST_STATE/pw-play-args"
                """,
            )
            self.command(directory, "sleep", "#!/bin/sh\nexit 0\n")

            result = self.run_session_sound(directory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((directory / "wpctl-calls").read_text().strip(), "3")
            arguments = (directory / "pw-play-args").read_text(encoding="utf-8")
            self.assertIn("--volume=0.45", arguments)
            self.assertIn("desktop-login.wav", arguments)

    def test_does_not_play_when_sink_is_muted(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.command(directory, "wpctl", "#!/bin/sh\nprintf 'Volume: 0.40 [MUTED]\\n'\n")
            self.command(
                directory,
                "pw-play",
                "#!/bin/sh\ntouch \"$LC300A_AUDIO_TEST_STATE/played\"\n",
            )

            result = self.run_session_sound(directory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((directory / "played").exists())


if __name__ == "__main__":
    unittest.main()
