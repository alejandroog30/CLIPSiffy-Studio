# Visualizations & Analytics

The IDE excels at translating abstract CLIPS logic into visual engineering graphics. These tools allow you to visually debug and analyze the mathematical behavior of your fuzzy systems without leaving the environment.

> **Note**: You can toggle which visualizations are generated via the `Settings` menu to save processing power during massive simulations.

## Block Diagram (System Topology)

Located on the right side of the screen, this interactive canvas automatically renders the architecture of your fuzzy systems based on the loaded facts.

- **Topological Layout**: Systems are drawn logically. If System A connects to System B, the diagram automatically routes the data flow clearly.

- **Nodes**: Dark blue boxes represent Inputs, purple boxes represent the Core System, and orange boxes represent Outputs.

- **Mini-Plots**: The input and output variable boxes feature embedded graphical previews of their mathematical Fuzzy Sets. Solid lines represent standard Type-1 sets, while Type-2 sets display the Footprint of Uncertainty (FOU) with dashed upper and solid lower bounds.

- **Interactivity**: You can click and drag any block to manually organize your diagram. The connection wires will dynamically update.

## Inference Viewer (2D Fuzzy Logic Execution)

When you run a fuzzy system and rules are fired, the FUZZY INFERENCE panel will automatically generate an interactive grid of plots detailing the exact mathematical steps taken by the engine.

- **Rows & Columns**: Each row represents a fired rule. Columns represent the input variables and the final output variable.

- **Visual Cuts**: It shows exactly where the Crisp Input intersects the Fuzzy Set (marked with a red line) and how the set is truncated or scaled based on the rule's strength (highlighted with blue/orange fills).

- **Defuzzification**: The bottom-right plot shows the aggregated area of all rules and the final computed crisp numerical result (marked with a thick green line).

- **Interactive Canvas**: Use the built-in toolbar at the top of the viewer to pan around the graphs, zoom into specific rule evaluations, or save the figure as an image.

## 3D Control Surface

If enabled (`Settings -> Generate 3D Control Surface`), the IDE will calculate and render the entire operational envelope of your fuzzy system.

- **Requirements**: Your system must have exactly 2 Input variables and 1 Output variable.

- **Visualization**: Generates an interactive, rotatable 3D topographic map plotting the two inputs on the X and Y axes, and the resulting defuzzified output on the Z-axis. This is critical for spotting "dead zones" or aggressive spikes in your controller's logic.

## Simulation Dashboard (Time-Series)

For environments running over multiple time steps, you can enable the SIMULATION DASHBOARD (`Settings -> Generate Simulation Dashboard`).

- It automatically tracks any `EnvHistory` facts generated during execution.

- Plots the evolution of your environment variables over time, allowing you to watch values rise, fall, or stabilize as your fuzzy system interacts with the environment.

## State Space (Phase Portrait)

A crucial tool for control systems engineering, enabled via `Settings -> Generate State Space Graph`.

- Instead of plotting variables against time, it plots one environment variable against another (e.g., Angle on the X-axis vs. Velocity on the Y-axis).

- **Trajectory Tracking**: Visualizes the dynamical trajectory of the system, clearly marking the "Start" state (green dot) and the "End" state (red dot) so you can see if your controller successfully drove the system to a stable equilibrium.