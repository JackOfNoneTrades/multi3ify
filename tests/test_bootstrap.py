from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.build_metadata import ROOT


class BootstrapTests(unittest.TestCase):
    def test_real_java_install_upgrade_rollback_and_offline_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            classes = Path(tmp) / "classes"
            classes.mkdir()
            sources = sorted(str(p) for p in (ROOT / "bootstrap").rglob("*.java"))
            subprocess.run(["javac", "--release", "8", "-Xlint:-options", "-d", str(classes), *sources], check=True)
            subprocess.run(["java", "-cp", str(classes),
                            "io.github.jackofnonetrades.multi3ify.BootstrapTest", tmp], check=True)


if __name__ == "__main__":
    unittest.main()
