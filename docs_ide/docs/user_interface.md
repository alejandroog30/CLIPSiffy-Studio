# Workspace & User Interface

The IDE is composed of modular, dockable panels that you can rearrange, detach into floating windows, or hide completely according to your needs.

## The Activity Bar

Running down the far left side of the window is the Activity Bar. This is your main navigation hub. Clicking the icons here will toggle the visibility of the various side panels, keeping your workspace clean when you need to focus on code.

- Use it to quickly switch between the File Explorer, the Fuzzy & Environment Builders, and your Memory Inspection panels (Facts, Rules, Agenda).

## The Code Editor

The central workspace where you write your `.clp` scripts.

- **Syntax Highlighting**: Automatically color-codes CLIPS constructs (`defrule`, `deffacts`, etc.), variables (`?var`), strings, and comments.

- **Smart Auto-Completion**: As you type, a dropdown will suggest CLIPS keywords as well as custom variables and rule names you have already typed in your document.

- **Code Folding**: You can collapse and expand large (`defrule ...`) blocks using the `[-]` and `[+]` icons in the line number margin to keep your view organized.

- **Bracket Matching**: Automatically closes parentheses `()` and intelligently skips over existing closing brackets to speed up your typing.

- **Unsaved Changes**: Tabs with unsaved changes are marked with an asterisk (`*`).

## Terminal and Problems Console

Located at the bottom of the screen, this panel acts as the standard output (`stdout`) and router for the CLIPS engine. It is split into two tabs:

- **Terminal**: Displays the standard execution logs, traces, and results. It features a Live Command Line at the bottom where you can type CLIPS commands directly (use the `Up` and `Down` arrows to navigate your command history).

- **Problems**: A dedicated tab that captures and isolates engine errors or syntax warnings in red, making it easy to debug without hunting through standard output logs.

- *Tip*: Right-click anywhere in the terminal to clear the screen or press `Ctrl+L`.

## File Explorer

The left-hand panel manages your project files.

- **Checkboxes**: Crucial feature. Only files with a checked box will be loaded into the engine when you trigger the `Load` command.

- **Interaction**: Double-click a file to open it in the Editor.

- **Context Menu**: Right-click to create a `New File`, `New Folder`, `Rename`, or `Delete` items directly from the IDE.

## Memory Inspection Panels

These panels provide a live view of the CLIPS engine's internal state. They update automatically every time you run a command or execute the environment.

- **FACTS**: Displays a raw list of standard CLIPS facts currently in memory.

- **RULES**: Displays a list of all compiled rules across all modules.

- **AGENDA**: Shows the list of rules that are currently activated and waiting to be fired, ordered by their salience (priority).

- **FUZZY FACTS**: A structured, hierarchical tree view that categorizes fuzzy-specific templates (e.g., `FuzzySystemConfig`, `FuzzyVar`, `FuzzySet`, `CrispInput`).

## Layouts, Themes & Customization

You can tailor the IDE to your preferences using the `View` menu:

- **Dark / Light Theme**: Toggle `View -> Dark Theme` to switch between a high-contrast dark mode (default) and a crisp light mode.

- **Zoom**: Use `Ctrl++` and `Ctrl+-` to increase or decrease the text size across both the code editors and the console.

- **Default Layout**: Displays the Explorer, Editor, Terminal, Memory Panels, and Diagram blocks spread across the screen.

- **Simple Layout**: Hides the Fuzzy tools and visual diagrams, leaving a clean, classic IDE (Editor + Terminal + Facts/Rules).