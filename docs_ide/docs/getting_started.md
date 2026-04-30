# Getting Started

## Installation and Execution

CLIPSiffy Studio is designed to be fully portable. If you have the standalone executable (`.exe`), simply double-click it to launch the environment. No Python installation or external dependencies are required.

> **Note:** Depending on your system settings, Windows SmartScreen might flag the executable since it is a custom application. If prompted, click "More info" and then "Run anyway" to launch the IDE.

## The Basic Workflow

To get your first expert system running, follow this standard workflow:

1. **Open a Project**: Click `File -> Open Folder...` (or `Ctrl+K, Ctrl+O`) to select your working directory.

2. **Select Files**: In the Explorer panel on the left, check the boxes next to the `.clp` files you want to load into the engine.

3. **Load (F4)**: Press `F4` to compile the selected files into the CLIPS memory.

4. **Reset (F5)**: Press `F5` to initialize facts and the agenda.

5. **Run (F6)**: Press `F6` to execute the rules. Watch the Console and the Inference Viewer for your results!

Once the system runs, you can monitor your results in the Console, or interact with the various visual dashboards like the Inference Viewer, 3D Surface, or State Space tools.