import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class InstallTests(unittest.TestCase):
    def test_installer_copies_skill_to_named_directory(self):
        with tempfile.TemporaryDirectory(prefix="discussion-install-") as tmp:
            target = Path(tmp) / "skills"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "install.py"), "--target", str(target), "--force"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            installed = target / "writing-result-centered-discussion"
            self.assertTrue((installed / "SKILL.md").exists())
            self.assertTrue((installed / "scripts" / "discussion.py").exists())
            self.assertNotIn("__pycache__", [p.name for p in installed.rglob("__pycache__")])


if __name__ == "__main__":
    unittest.main()
