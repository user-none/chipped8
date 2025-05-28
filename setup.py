import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
from compile_shaders import compile_shaders

class build_py(_build_py):
    def run(self):
        compile_shaders()
        super().run()

setup(
    cmdclass={
        'build_py': build_py,
    }
)
