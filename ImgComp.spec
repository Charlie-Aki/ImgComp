# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['ImgComp_v7-1.py'],
             pathex=['C:\\Users\\charl\\Documents\\python_project\\aida'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['./hook'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='画像比較',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , icon='C:\\Users\\charl\\Documents\\python_project\\aida\\imgs\\ImgComp_256x256.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='画像比較')
