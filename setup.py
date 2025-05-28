import os
import subprocess

from itertools import chain
from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

class build_py(_build_py):
    def run(self):
        self.compile_shaders()
        super().run()

    def compile_shaders(self):
        project_root = Path(__file__).parent.resolve()
        shaders_dir = Path('chipped8', 'gui', 'shaders')
        qsb = shutil.which('pyside6-qsb')
        print(f'======= qsb = "{qsb}"')

        for shader in chain(shaders_dir.glob('*.vert'), shaders_dir.glob('*.frag')):
            output = shader.with_name(shader.name + ".qsb")
            if not output.exists() or shader.stat().st_mtime > output.stat().st_mtime:
                print(f'Compiling {shader.name} -> {output.name}')
                subprocess.run([
                    qsb,
                    '--glsl', '100 es,120,150',#'450',
                    '--hlsl', '50',
                    '--msl', '12',
                    '-c',
                    '-o', str(output),
                    str(shader)
                ], check=True)

setup(
    cmdclass={
        'build_py': build_py,
    }
)
