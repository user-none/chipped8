# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

import sys
import tomllib

datas = [('../chipped8/gui/qml', 'chipped8/gui/qml')]
datas += copy_metadata('chipped8')

# Load toml with project information
tomldata = None
with open("pyproject.toml", "rb") as f:
    tomldata = tomllib.load(f)
project_name = tomldata.get('project').get('name')
project_version = tomldata.get('project').get('version')
authors = tomldata.get('project').get('authors')
project_authors = []
for author in authors:
    project_authors.append(author.get('name'))

if sys.platform == "darwin":
    icon_file = 'logo.icns'
elif sys.platform == "win32":
    icon_file = 'logo.ico'
else:
    icon_file = ''

a = Analysis(
    ['runner.py'],
    pathex=['../chipped8'],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=project_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[icon_file],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=project_name,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f'{project_name}.app',
        icon='logo.icns',
        bundle_identifier=None,
        info_plist = {
            'CFBundleDevelopmentRegion': 'English',
            'CFBundleExecutable': project_name,
            'CFBundleDisplayName': project_name,
            'CFBundleGetInfoString': project_name,
            'CFBundleName': project_name,
            'CFBundleIconFile': 'logo.icns',
            'CFBundleIdentifier': 'user_none.chipped8',
            'CFBundleShortVersionString': project_version,
            'CFBundleVersion': project_version,
            'CFBundleLongVersionString': project_version,
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeExtensions': [ 'ch8' ],
                    'CFBundleTypeName': 'CHIP-8 Rom',
                    'CFBundleTypeRole': 'Viewer',
                    'LSHandlerRank': 'Default'
                }
            ],
            'CFBundleInfoDictionaryVersion': '6.0',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': '????',
            'NSHighResolutionCapable': True,
            'CSResourcesFileMapped': True,
            'NSHumanReadableCopyright': 'Copyright © 2024 {0} and Contributors'.format(', '.join(project_authors)),
            'LSApplicationCategoryType': 'public.app-category.games',
            'LSMinimumSystemVersion': '14.0'
        }
    )
