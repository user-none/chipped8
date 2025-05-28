import subprocess
import shutil
from pathlib import Path
from itertools import chain

def compile_shaders():
    qsb = shutil.which('pyside6-qsb')
    if not qsb:
        raise RuntimeError('pyside6-qsb executable not found on PATH')

    shaders_dir = Path(__file__).resolve().parent.parent / 'chipped8' / 'gui' / 'shaders'
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

if __name__ == '__main__':
    compile_shaders()
