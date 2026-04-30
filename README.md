# CLIPSiffy-Studio

## Installation

To install this project as an executable, use the following command:

```bash
pyinstaller --onefile --name "CLIPSiffy Studio" --noconsole --icon="images/icon.ico" --exclude-module PySide6 --hidden-import cffi --hidden-import _cffi_backend --collect-all qtvscodestyle --add-data "docs_ide;docs_ide" --add-data "fuzzy_lib;fuzzy_lib" --add-data "images;images" main.py
```