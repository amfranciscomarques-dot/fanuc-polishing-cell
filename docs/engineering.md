# Engineering notes

[Back to the project](../README.md)

## Objective and design choices

Build a small, reproducible robot simulation that communicates a complete polishing sequence. A fixed workpiece and a wrist-mounted tool keep the scene and its coordinate frames easy to inspect. Five passes provide a visible coverage pattern while keeping the program at 37 instructions.

The project uses a representative cover and a conceptual polisher. The selected tool and speeds demonstrate programming choices; they are not a process recipe for a particular abrasive or aluminium alloy.

## Frames and geometry

All lengths are in millimetres. All station frames have parallel axes before tool orientation is applied.

| Frame / component | Translation relative to station origin |
|---|---|
| Robot kinematic base | X = 0, Y = 0, Z = 500 |
| Workpiece frame | X = 850, Y = 0, Z = 590 |
| Table top surface | Z = 560 |
| Workpiece top centre | X = 850, Y = 0, Z = 620 |
| TCP relative to flange | X = 0, Y = 0, Z = 200 |

The imported library model's kinematic origin is 450 mm above its mounting face, so the base frame at Z = 500 places the mounting face on the 50 mm plate. The builder resets the model's embedded demonstration-frame offset and updates the scene before computing inverse kinematics.

The workpiece frame relative to the robot base is therefore `[850, 0, 90]`. These values also appear in the `.LS` export's UFRAME comment.

## Surface and path

The upper surface is extruded along Y and defined by:

```text
z(x) = 30 − 4(x / 150)²
dz/dx = −8x / 22500
```

The mesh spans X = −150…150 and Y = −100…100. Its maximum thickness is 30 mm and its end thickness is 26 mm.

The programmed tool centres use:

```text
X points: −130, −65, 0, 65, 130
Y passes: −80, −40, 0, 40, 80
```

The order of X points reverses on alternate passes. With an 80 mm pad and 40 mm spacing, the nominal overlap is 50%. Pad overhang at the part edges is intentional in this concept. This geometric pattern is not a measured material-removal coverage result.

At each target, tool orientation is:

```text
T = Trans(x, y, z(x) + lift) · Ry(−atan(dz/dx)) · Rx(π)
```

This points the tool's Z axis toward the surface and aligns it with the surface normal. The five points per pass approximate the smooth crown with straight segments; at a 65 mm spacing, the surface-to-chord height difference is about 0.188 mm before blending. Disc compliance is not modelled.

## Program sequence

| Stage | Motion / action |
|---|---|
| Setup | Select work frame and TCP; set rounding and speeds |
| Home | Joint move to 220 mm above the first surface point |
| Approach | Joint move to 80 mm above the first surface point |
| Tool on | Set simulated `DO[1] = ON` |
| Polish | Linear entry and 25 path points at 40 mm/s |
| Retract | Linear move to 80 mm above the final surface point |
| Tool off | Set simulated `DO[1] = OFF` |
| Return | Joint move to home |

The initial joint setting is 30 °/s. The 100 mm/s setup value does not determine the speed of the joint moves. The polishing and retract moves use 40 mm/s. RoboDK rounding is set to 1 mm; the postprocessor emits FANUC `CNT1`, whose controller semantics differ from a physical 1 mm blend radius.

## Recorded verification

The published [`verificacao.json`](../verificacao.json) records:

- RoboDK 6.0.6.26902, using a Free (Trial) licence.
- 37 instructions and a valid-path ratio of 1.0.
- No collision reported by the path check at 5 mm linear / 3° angular sampling.
- A completed simulator run at 1× and zero collisions at its final pose.
- Approximately 54.2 seconds of observed simulator runtime.

The collision map excludes tool–workpiece contact and the attached tool–flange pair. The tool is one collision item, so the tool–workpiece exclusion covers its entire geometry, not just the abrasive pad. Consequently, this check cannot detect unintended tool-body contact with the workpiece. Sampling also does not constitute continuous collision proof.

The API estimated approximately 11.95 seconds, which differed from observed playback. Both values are retained as evidence; no validated production cycle time is claimed.

## Export status

The FANUC R30i postprocessor wrote `POLIR.LS`, with 38 `/MN` lines, 29 position records and a closing `/END` marker. Its API completion flag was `False`, with an empty log. The text file is provided as an example, without claiming successful `.TP` compilation or controller compatibility validation.

It selects UFRAME[1] and UTOOL[1] but does not configure those registers. Output DO[1] is an illustrative tool signal. No physical I/O allocation or robot deployment has been performed.

## Reproduction boundaries

The builder creates and checks the station, writes the part STL and captures the overview. The committed working-pose image, simulator-run observation and export evidence came from separate steps in the original session. A rebuild replaces `verificacao.json` with the newly computed path-check record; it does not reproduce those additional observations automatically.

This project does not model force control, pad deflection, spindle dynamics, workholding strength, dust extraction, guarding interlocks or finish quality. Extending it to a physical cell would require engineering and validation of those aspects.
