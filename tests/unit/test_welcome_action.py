import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WELCOME_ACTION = PROJECT_ROOT / "distro/overlays/usr/local/bin/lc300a-welcome-action"
WELCOME_LAUNCHER = PROJECT_ROOT / "distro/overlays/usr/local/bin/lc300a-welcome"


class WelcomeActionTest(unittest.TestCase):
    def command(self, directory: Path, name: str) -> None:
        path = directory / name
        path.write_text(
            textwrap.dedent(
                f"""
                #!/bin/sh
                printf '%s\\n' "$*" >"$LC300A_WELCOME_TEST_STATE/{name}-args"
                """
            ).lstrip(),
            encoding="utf-8",
        )
        path.chmod(0o755)

    def run_action(
        self, directory: Path, action: str
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = f"{directory}:/usr/bin:/bin"
        environment["XDG_CONFIG_HOME"] = str(directory / "config")
        environment["LC300A_WELCOME_TEST_STATE"] = str(directory)
        return subprocess.run(
            ["/bin/sh", str(WELCOME_ACTION), action],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_rejects_unknown_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = self.run_action(directory, "lc300a-action:unknown")
            self.assertEqual(result.returncode, 2)
            self.assertFalse((directory / "config").exists())

    def test_opens_only_known_desktop_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.command(directory, "systemsettings")
            self.command(directory, "plasma-discover")

            settings = self.run_action(directory, "lc300a-action:settings")
            apps = self.run_action(directory, "lc300a-action:apps")

            self.assertEqual(settings.returncode, 0, settings.stderr)
            self.assertEqual(apps.returncode, 0, apps.stderr)
            self.assertEqual((directory / "systemsettings-args").read_text(), "\n")
            self.assertEqual((directory / "plasma-discover-args").read_text(), "\n")

    def test_finish_writes_private_completion_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = self.run_action(directory, "lc300a-action:finish")

            state = directory / "config/lc300a/welcome-complete"
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(state.read_text(encoding="utf-8"), "completed=true\n")
            self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o600)

            environment = os.environ.copy()
            environment["XDG_CONFIG_HOME"] = str(directory / "config")
            skipped = subprocess.run(
                ["/bin/sh", str(WELCOME_LAUNCHER), "--first-login"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(skipped.returncode, 0, skipped.stderr)


if __name__ == "__main__":
    unittest.main()
