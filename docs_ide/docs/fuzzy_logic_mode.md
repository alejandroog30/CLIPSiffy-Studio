# Fuzzy Logic Mode & The Fuzzy Builder

This is the flagship feature of the IDE. When enabled via `Settings -> Enable Fuzzy Logic Mode`, the IDE automatically injects a background library to support advanced fuzzy logic operations and unlocks the Builder panels.

## The Fuzzy Builder Panel

This tool allows you to visually design Fuzzy Systems without writing raw CLIPS code. It acts as a live UPSERT (Update/Insert) tool: if a fact with the same ID or Name exists, the Builder will overwrite it; otherwise, it creates a new one.

1. **FuzzySystemConfig**: Define the system ID, Method (Mamdani/Sugeno), Type (1 or 2), and defuzzification algorithms.

2. **FuzzyVar**: Define inputs and outputs, linking them to a specific System ID, along with their Min/Max ranges.

3. **FuzzySet**: Create linguistic labels (e.g., "Cold", "Fast"). Supports Triangular, Trapezoidal, Gaussian, Gamma, Z, S, and L curves. For Type-2, you can define Upper (`u-mf`) and Lower (`l-mf`) bounds.

4. **CrispInput**: Inject real-world numerical values into your system variables.

5. **Connection**: Define data flow between the output of one system and the input of another.

6. **LinguisticModifier**: Apply hedges (e.g., `mod-very`, `mod-somewhat`) to existing fuzzy sets.

> _Note: The forms feature auto-completion. If you type an existing System ID or Variable name, the IDE will fetch its current data from CLIPS memory and pre-fill the form for you to edit._

## Fuzzy Rule Logic Injector

The last option in the Builder dropdown is the Fuzzy Rule. It provides a text editor that translates standard human-readable logic into native CLIPS `defrule` syntax.

Syntax Rules:

- Must start with `IF` and contain `THEN`.

- Use `AND` / `OR` to combine antecedents.

- Format: `VarName=LabelName`.

Mamdani Example:

```clips
IF Temperature=Cold AND Humidity=High THEN FanSpeed=Fast
```

Sugeno Example:

For Sugeno systems, the consequent must be a mathematical expression (using variables defined in the antecedents).

```clips
IF Temperature=Cold THEN FanSpeed=10+Temperature*1.5
```

Once typed, click ADD / UPDATE to compile and inject the rule directly into the engine.

## FAM Matrix Editor (2D Rule Grid)

For rapid rule generation, click the OPEN 2D FAM MATRIX EDITOR button inside the Fuzzy Rule form.

- **Requirements**: Your system must have exactly 2 input variables and 1 output variable.

- **Mamdani Mode**: The dialog provides a grid where rows are the first input's sets and columns are the second input's sets. Simply select the desired output label from the dropdowns.

- **Sugeno Mode**: The grid provides text boxes where you can type your mathematical equations or crisp values.

- Upon clicking OK, the IDE automatically translates the entire table into pseudo-code and injects the rules into the CLIPS memory instantly.

## Environment Builder

Located in the ENVIRONMENT BUILDER panel, this interface lets you define simulation loops and physics without touching CLIPS syntax.

- **EnvConfig**: Define your simulation's environment ID, Maximum Steps, and the Time Delta (`dt`) for each tick.

- **EnvVar**: Track internal state variables (like position or temperature) and set their initial values.

- **EnvEquation**: Define mathematical formulas to update your target variables on each step (e.g., Target: `velocity`, Update Func: `+`, Args: `acceleration dt`).

- **EnvLink**: Connect your environment's variables directly into the inputs of your fuzzy systems.

## Export Fuzzy Configuration

Go to `File -> Export Fuzzy Configuration...` (`Ctrl+E`). This tool scans the live CLIPS memory and generates a clean `.clp` file containing all your visually created Fuzzy Systems, Variables, Sets, and compiled Rules. It opens the result in a new tab so you can save it to your project.