import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

import subprocess
import shutil
from pathlib import Path
from itertools import chain

class build_py(_build_py):
    def compile_shaders(self):
        qsb = shutil.which('pyside6-qsb')
        if not qsb:
            raise RuntimeError('pyside6-qsb executable not found on PATH')

        shaders_dir = Path(__file__).parent.resolve() / 'chipped8' / 'gui' / 'shaders'
        for shader in chain(shaders_dir.glob('*.vert'), shaders_dir.glob('*.frag')):
            output = shader.with_name(shader.name + '.qsb')
            if not output.exists() or shader.stat().st_mtime > output.stat().st_mtime:
                print(f'Compiling {shader.name} -> {output.name}')
                subprocess.run([
                    qsb,
                    '--glsl', '100 es,120,150',
                    '--hlsl', '50',
                    '--msl', '12',
                    '-c',
                    '-o', str(output),
                    str(shader)
                ], check=True)

    def run(self):
        self.compile_shaders()
        super().run()

setup(
    cmdclass={
        'build_py': build_py,
    }
)
