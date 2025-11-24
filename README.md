# MCNP Universe & Lattice Wizard

A Python-based interactive wizard for generating proper universe specifications for MCNP tallies and source definitions.

## Overview

This tool solves a common MCNP problem: correctly specifying nested universe paths for tallies and source definitions. MCNP's syntax for universe referencing is strict and error-prone, especially when dealing with lattices. This wizard guides you through the process step-by-step.

## Features

-  **Interactive Q&A Interface** - Walks you through building universe specifications
-  **Bottom-Up Approach** - Builds the universe stack from target to global universe
-  **Tally Generation** - Creates proper F-card specifications with `<` operator syntax
-  **SDEF Generation** - Uses robust distribution method (SI/SP cards)
-  **Lattice Support** - Handles LAT=1 and LAT=2 lattices with proper index notation
-  **SD Card Detection** - Warns when segment divisor cards are required
-  **Verification Output** - Generates test deck snippets for validation
-  **Modern MCNP6 Syntax** - Uses current standards (no deprecated `:` syntax)

## Installation

### Requirements
- Python 3.7 or higher
- NumPy (for future coordinate transformation features)
- If Windows, requires Curses. 

```bash
pip install numpy
```

### Quick Start
```bash
# Download the wizard
chmod +x mcnp_wizard.py

# Run it
python mcnp_wizard.py
```

## Usage

### Basic Workflow

1. **Run the wizard:**
   ```bash
   python mcnp_wizard.py
   ```

2. **Choose output type:**
   - Tally specification (F4, F7, etc.)
   - Source definition (SDEF)
   - Both

3. **Answer questions about your geometry:**
   - Target cell ID
   - Parent cells (working outward)
   - Lattice indices (if applicable)
   - Universe numbers

4. **Get your specification:**
   - Copy/paste ready MCNP cards
   - SD card if needed
   - Verification deck

### Example 1: Simple Nested Universe

**Scenario:** Tally flux in a fuel pin (Cell 5) inside an assembly (Cell 2) inside a core (Cell 1).

**Wizard Session:**
```
What is the specific cell ID you want to tally/source? 5
Is Cell 5 inside a universe (not Universe 0)? y
What universe number is Cell 5 in? 10

What cell FILLS universe 10? 2
Is Cell 2 a lattice? n
Is Cell 2 inside a universe (not Universe 0)? y
What universe number is Cell 2 in? 100

What cell FILLS universe 100? 1
Is Cell 1 a lattice? n
Is Cell 1 inside a universe (not Universe 0)? n
```

**Generated Output:**
```
F4:N ( 5 < 2 < 1 )
```

### Example 2: Lattice with Indices

**Scenario:** Tally in a pin (Cell 101) at lattice position [3, 4, 0] in assembly (Cell 50), inside core (Cell 1).

**Generated Output:**
```
F4:N ( 101 < 50[3 4 0] < 1 )
SD4 2.5  $ Volume you provided
```

### Example 3: Source Definition

**Scenario:** Place a source in the same nested cell as Example 1.

**Generated Output:**
```
SDEF CEL=d1 ERG=1.0
SI1 L ( 5 < 2 < 1 )
SP1 1
```

## Understanding the Output

### Tally Syntax: The `<` Operator

The `<` operator means "when contained in". The syntax is **bottom-up** (innermost first):

```
( Target < Parent < Grandparent < ... < Global )
```

**Key Rules:**
- Target cell comes first
- Parent cells follow in order
- Lattice indices `[i j k]` immediately follow the cell ID
- Use spaces, not commas: `Cell[1 2 3]` not `Cell[1,2,3]`
- Entire path in parentheses: `( ... )`

### SDEF Syntax: Distribution Method

Instead of putting complex paths directly on the SDEF card, the wizard uses distributions:

```
SDEF CEL=d1 [other parameters]
SI1 L ( path specification )
SP1 1
```

This is more robust and less prone to parsing errors.

### SD Cards (Segment Divisor)

**When do you need an SD card?**
- When tallying in a cell that is inside a lattice
- MCNP cannot auto-calculate volumes for individual lattice elements
- Without SD, MCNP defaults to volume = 1.0 (wrong results!)

**What to do:**
1. Calculate the actual volume of your target cell (in cm³)
2. Add the SD card: `SD4 <volume>` (for F4 tally)

## Verification

The wizard can generate a verification deck snippet. Here's how to use it:

1. **Generate verification output** when prompted
2. **Copy the snippet** into a test input file
3. **Set all materials to void** (or use M0)
4. **Run MCNP** with NPS 50
5. **Check PRINT 110 output** in the output file
6. **Look for "source particle" lines** - they should show:
   - Correct starting cell
   - Correct lattice indices
   - No "lost particles" or Cell 0 warnings

If particles are lost or in the wrong cell, your specification needs correction.

## Architecture

### Data Structure: Universe Stack

The wizard builds a **stack** (list) of `Node` objects, each representing:

```python
@dataclass
class Node:
    cell_id: int                               # Cell number
    universe_id: Optional[int]                 # Universe this cell is in
    fill_id: Optional[int]                     # Universe that fills this cell
    is_lattice: bool                           # Is this a lattice?
    lattice_index: Optional[Tuple[int, int, int]]  # [i, j, k] if lattice
    transform: Optional[np.ndarray]            # For coordinate transforms
```

### Algorithm: Reverse Recursion

The wizard uses a **bottom-up** approach:

1. Start at the target (innermost cell)
2. Ask "What cell contains this universe?"
3. If that cell is a lattice, get the indices
4. Ask "What universe is that cell in?"
5. Repeat until reaching Universe 0 (global)

## Advanced Features (Future If I Want)

### Coordinate Transformation (Future)
- [ ] Calculate global coordinates from local position
- [ ] Apply TRCL/TR transformations
- [ ] Enable accurate POS specification for SDEF or KSRC

### MCNP File Integration (Future)
- [ ] Read existing MCNP input files, point at cell and will auto trace basic structure. - montepy imp?
- [ ] Auto-detect universe structure
- [ ] Integrate with MontePy library
- [ ] Validate cell IDs exist

## Troubleshooting

### Common Issues

**Problem:** "Particles are lost" when running verification
- **Solution:** Double-check cell IDs and universe numbers match your input deck

**Problem:** "Wrong cell in output"
- **Solution:** Verify lattice indices are correct

**Problem:** "Tally results seem wrong"
- **Solution:** Did you add the SD card? Check if volume is correct

**Problem:** "MCNP syntax error"
- **Solution:** Make sure you're using MCNP6. Older versions may use `:` syntax

### Getting Help

1. Check the MCNP manual (Chapter 3, Section on Universe)
2. Use PRINT 110 to debug source positions
3. Start simple (no lattices) and add complexity
4. Test with small NPS first

## Technical Notes

### LSTE Compatibility

The wizard generates syntax compatible with the **Lattice Speed Tally Enhancement** (LSTE):
- Uses explicit cell IDs (no wildcards like `U=3`)
- Follows modern MCNP6 conventions
- Can provide 10-100x speedup for lattice tallies

### Safety Features

- Input validation (integers only for cell IDs)
- Automatic SD card detection
- Clear warnings for missing volume data
- Verification output to catch errors early

## Examples Library

### Example 4: Complex Multi-Level Lattice

**Geometry:**
- Fuel pellet (Cell 1001) in Universe 1
- Pin (Cell 500) fills U=1, is in Universe 10
- Assembly (Cell 200) is LAT=1, fills U=10 at index [5,5,0], is in U=100
- Core (Cell 50) fills U=100, is in U=0

**Output:**
```
F4:N ( 1001 < 500 < 200[5 5 0] < 50 )
```

### Example 5: Source in Lattice Element

**SDEF for same geometry:**
```
SDEF CEL=d1 ERG=2.0 POS=0 0 0
SI1 L ( 1001 < 500 < 200[5 5 0] < 50 )
SP1 1
```

## Credits

Based on technical specifications for proper MCNP6 universe and lattice syntax. Designed to prevent common errors in nested geometry definitions.

---

**Version:** 1.0.0  
**Author:** MCNP Community  
**Last Updated:** November 2024
