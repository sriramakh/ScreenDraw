"""
Generate a Windows version info file for PyInstaller.
This embeds version metadata into the .exe (visible in Properties dialog).

Reads version from the VERSION file in the project root.

Usage: python version_info.py
Output: file_version_info.txt (used by PyInstaller --version-file)
"""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# Read version from VERSION file
version_file = os.path.join(ROOT_DIR, "VERSION")
if os.path.exists(version_file):
    VERSION = open(version_file).read().strip()
else:
    VERSION = "1.0.0"

# Ensure 4-part version for Windows
parts = VERSION.split(".")
while len(parts) < 4:
    parts.append("0")
VERSION_4 = ".".join(parts[:4])
VERSION_TUPLE = ", ".join(parts[:4])

COMPANY = "ScreenDraw"
PRODUCT = "ScreenDraw"
DESCRIPTION = "Live Screen Drawing & Annotation Tool"
COPYRIGHT = "Copyright (c) 2024-2026 ScreenDraw"
ORIGINAL_FILENAME = "ScreenDraw.exe"

template = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({VERSION_TUPLE}),
    prodvers=({VERSION_TUPLE}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'{COMPANY}'),
            StringStruct(u'FileDescription', u'{DESCRIPTION}'),
            StringStruct(u'FileVersion', u'{VERSION_4}'),
            StringStruct(u'InternalName', u'{PRODUCT}'),
            StringStruct(u'LegalCopyright', u'{COPYRIGHT}'),
            StringStruct(u'OriginalFilename', u'{ORIGINAL_FILENAME}'),
            StringStruct(u'ProductName', u'{PRODUCT}'),
            StringStruct(u'ProductVersion', u'{VERSION_4}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

def generate():
    output_path = os.path.join(SCRIPT_DIR, "file_version_info.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)
    print(f"Version info saved to: {output_path}")

if __name__ == "__main__":
    generate()
