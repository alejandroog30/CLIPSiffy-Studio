# Execution & Debugging

The `Run` and `Debug` menus contain the core commands to control the CLIPS engine, monitor its internal state, and hunt down logic errors.

## Controlling the Engine (The Run Menu)

Because the IDE runs the CLIPS engine on a background thread, your interface will never freeze during heavy simulations, allowing you to monitor and halt execution in real-time.

- **Load Environment (F4)**: Compiles the files currently checked in the File Explorer into the engine. If no files are checked, it attempts to load the currently active file in the Editor. Note: If Fuzzy Logic Mode is enabled, this also injects the necessary background fuzzy libraries automatically.

- **Reset (F5)**: Executes the CLIPS `(reset)` command. It clears standard facts and asserts your initial facts from `deffacts` constructs, preparing the system for a fresh run.

- **Run (F6)**: Executes the CLIPS `(run)` command, continuously firing activated rules on the agenda until none are left.

- **Step (F7)**: Executes `(run 1)`, firing exactly one rule and then pausing. This is ideal for debugging infinite loops or tracking the exact order of rule execution.

- **Stop Execution (Shift+F6)**: Safely halts a running simulation without crashing the application.

- **Clear Environment (Ctrl+Shift+L)**: Completely wipes the CLIPS memory, removing all rules, facts, and templates.

## The Dual Console

Located at the bottom of the screen, the Console is your primary debugging window, uniquely split into two tabs to keep information organized:

- **Terminal**: Displays standard output, `printout` statements, and engine traces. You can also type raw CLIPS commands here manually.

- **Problems**: A dedicated tab that intercepts engine errors, syntax warnings, and runtime exceptions. Instead of getting lost in a sea of standard text, errors are isolated here and highlighted in bold red so you can spot and fix them immediately.

## Tracing Logic (The Debug Menu)

If your expert system is not behaving as expected, you can ask the CLIPS engine to explain exactly what it is doing behind the scenes using the `Debug` menu toggles:

- **Watch Facts**: Prints a message to the Terminal every time a fact is asserted or retracted.

- **Watch Rules**: Prints a message every time a rule fires.

- **Watch Activations**: Prints a message every time a rule is added to or removed from the Agenda (meaning its IF conditions have been met).

## Essential Keyboard Shortcuts

To speed up your workflow, memorize these core shortcuts:

- **F4**: Load Environment

- **F5**: Reset

- **F6**: Run

- **F7**: Step

- **Ctrl + S**: Save File

- **Ctrl + /**: Toggle Comment on selected text

- **Ctrl + L**: Clear Console