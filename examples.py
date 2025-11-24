#!/usr/bin/env python3
"""
Example demonstration of the MCNP Wizard
This script shows what the wizard generates for common scenarios.
"""

from mcnp_wizard import Node, MCNPWizard, LatticeSpec


def example_1_simple_nested():
    """
    Example 1: Simple nested universe (no lattice)
    Fuel pin in assembly in core
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Simple Nested Universe")
    print("=" * 70)
    print("\nScenario:")
    print("  - Fuel pin (Cell 5) in Universe 10")
    print("  - Assembly (Cell 2) fills U=10, is in Universe 100")
    print("  - Core (Cell 1) fills U=100, is in Universe 0")
    print()
    
    wizard = MCNPWizard()
    
    # Manually build the stack
    wizard.target_cell = 5
    wizard.universe_stack = [
        Node(cell_id=5, universe_id=10),
        Node(cell_id=2, universe_id=100, fill_id=10, is_lattice=False),
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]
    
    # Generate output
    path = wizard._build_tally_path()
    
    print("Generated Tally Specification:")
    print(f"  F4:N {path}")
    print()
    print("Explanation:")
    print("  - Start at Cell 5 (the target)")
    print("  - Cell 5 is contained in Cell 2")
    print("  - Cell 2 is contained in Cell 1")
    print("  - Cell 1 is in the global universe")
    print()


def example_2_lattice_simple():
    """
    Example 2: Single-level lattice
    Pin in lattice assembly in core
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Single-Level Lattice")
    print("=" * 70)
    print("\nScenario:")
    print("  - Fuel pin (Cell 101) in Universe 5")
    print("  - Assembly (Cell 50) is LAT=1, fills U=5 at index [3,4,0], in U=100")
    print("  - Core (Cell 1) fills U=100, is in Universe 0")
    print()

    wizard = MCNPWizard()

    wizard.target_cell = 101
    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             lattice_spec=LatticeSpec(i=3, j=4, k=0)),
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]
    
    path = wizard._build_tally_path()
    
    print("Generated Tally Specification:")
    print(f"  F4:N {path}")
    print()
    print("⚠ WARNING: Requires SD card!")
    print("  Cell 101 is inside a lattice - volume must be specified")
    print("  SD4 2.75  $ Volume of Cell 101 in cm³")
    print()
    print("Explanation:")
    print("  - Cell 101 is at lattice position [3 4 0]")
    print("  - Lattice indices must immediately follow cell ID: 50[3 4 0]")
    print("  - SD card needed because Cell 101 is in a lattice")
    print()


def example_3_multilevel_lattice():
    """
    Example 3: Multi-level lattice (lattice of assemblies)
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Multi-Level Lattice")
    print("=" * 70)
    print("\nScenario:")
    print("  - Pellet (Cell 1001) in Universe 1")
    print("  - Pin (Cell 500) fills U=1, is in Universe 10")
    print("  - Assembly (Cell 200) is LAT=1, fills U=10 at [5,5,0], in U=100")
    print("  - Core (Cell 50) is LAT=1, fills U=100 at [2,3,0], in U=0")
    print()
    
    wizard = MCNPWizard()
    
    wizard.target_cell = 1001
    wizard.universe_stack = [
        Node(cell_id=1001, universe_id=1),
        Node(cell_id=500, universe_id=10, fill_id=1, is_lattice=False),
        Node(cell_id=200, universe_id=100, fill_id=10, is_lattice=True,
             lattice_spec=LatticeSpec(i=5, j=5, k=0)),
        Node(cell_id=50, universe_id=0, fill_id=100, is_lattice=True,
             lattice_spec=LatticeSpec(i=2, j=3, k=0))
    ]
    
    path = wizard._build_tally_path()
    
    print("Generated Tally Specification:")
    print(f"  F4:N {path}")
    print()
    print("⚠ WARNING: Requires SD card!")
    print("  Cell 1001 is inside a lattice - volume must be specified")
    print("  SD4 0.35  $ Volume of Cell 1001 in cm³")
    print()
    print("Explanation:")
    print("  - Multiple lattice levels")
    print("  - Each lattice cell has its indices")
    print("  - Read right-to-left: Cell 1001 in Cell 500 in Cell 200[5 5 0]")
    print("    in Cell 50[2 3 0]")
    print()


def example_4_sdef_generation():
    """
    Example 4: SDEF card generation
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Source Definition (SDEF)")
    print("=" * 70)
    print("\nScenario: Place neutron source in Example 2 geometry")
    print()
    
    wizard = MCNPWizard()
    
    wizard.target_cell = 101
    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             lattice_spec=LatticeSpec(i=3, j=4, k=0)),
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]

    path = wizard._build_tally_path()

    print("Generated Source Definition:")
    print(f"  SDEF CEL=d1 ERG=1.0")
    print(f"  SI1 L {path}")
    print(f"  SP1 1")
    print()
    print("Explanation:")
    print("  - CEL=d1 tells MCNP to use distribution 1 for cell")
    print("  - SI1 L specifies a list (L) distribution with the path")
    print("  - SP1 1 gives 100% probability (only one option)")
    print("  - ERG=1.0 sets 1 MeV source energy")
    print()


def example_5_verification_deck():
    """
    Example 5: Verification deck snippet
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Verification Deck")
    print("=" * 70)
    print("\nPurpose: Test if your specification is correct")
    print()
    
    print("Steps to verify:")
    print("  1. Copy the verification snippet into a test input")
    print("  2. Set all materials to void (M0)")
    print("  3. Run with NPS 50")
    print("  4. Add PRINT 110 to get detailed source info")
    print("  5. Check output for 'source particle' lines")
    print()
    
    print("Example verification deck:")
    print("-" * 70)
    print("C --- Verification Test ---")
    print("SDEF CEL=d1 ERG=1.0")
    print("SI1 L ( 101 < 50[3 4 0] < 1 )")
    print("SP1 1")
    print("NPS 50")
    print("PRINT 110")
    print("C")
    print("C Set materials to void:")
    print("C Replace all material cards with M0 or comment them out")
    print("-" * 70)
    print()
    print("What to look for in output:")
    print("  ✓ Particles starting in Cell 101")
    print("  ✓ Correct lattice indices [3 4 0]")
    print("  ✗ Particles 'lost' or in Cell 0 (BAD - fix specification)")
    print()


def example_6_common_mistakes():
    """
    Example 6: Common mistakes to avoid
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Common Mistakes to Avoid")
    print("=" * 70)
    print()
    
    print("❌ WRONG: Using commas in lattice indices")
    print("   F4:N ( 101 < 50[3,4,0] < 1 )")
    print()
    print("✓ CORRECT: Use spaces")
    print("   F4:N ( 101 < 50[3 4 0] < 1 )")
    print()
    
    print("❌ WRONG: Lattice indices in wrong position")
    print("   F4:N ( 101 < [3 4 0] < 50 < 1 )")
    print()
    print("✓ CORRECT: Indices immediately after cell ID")
    print("   F4:N ( 101 < 50[3 4 0] < 1 )")
    print()
    
    print("❌ WRONG: Top-down ordering (outside-in)")
    print("   F4:N ( 1 < 50[3 4 0] < 101 )")
    print()
    print("✓ CORRECT: Bottom-up ordering (inside-out)")
    print("   F4:N ( 101 < 50[3 4 0] < 1 )")
    print()
    
    print("❌ WRONG: Forgetting SD card for lattice tally")
    print("   F4:N ( 101 < 50[3 4 0] < 1 )")
    print("   (No SD card -> MCNP uses volume = 1.0 -> Wrong results!)")
    print()
    print("✓ CORRECT: Include SD card")
    print("   F4:N ( 101 < 50[3 4 0] < 1 )")
    print("   SD4 2.75  $ Actual volume in cm³")
    print()


def example_7_lattice_ranges():
    """
    Example 7: NEW - Lattice range specification
    Demonstrates tallying over multiple lattice elements
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Lattice Range Specification (NEW!)")
    print("=" * 70)
    print("\nScenario: Tally flux in a 3x3 block of pins")
    print("  - Fuel pin (Cell 101) in Universe 5")
    print("  - Assembly (Cell 50) is LAT=1 (10x10 rectangular), in U=100")
    print("  - Want to tally pins at i=2:4, j=3:5, k=0")
    print("  - Core (Cell 1) fills U=100, is in Universe 0")
    print()

    wizard = MCNPWizard()

    wizard.target_cell = 101
    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             lattice_spec=LatticeSpec(i=(2, 4), j=(3, 5), k=0)),  # Range!
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]

    path = wizard._build_tally_path()

    print("Generated Tally Specification (with RANGES):")
    print(f"  F4:N {path}")
    print()
    print("⚠ WARNING: Requires SD card!")
    print("  Cell 101 is inside a lattice - volume must be specified")
    print("  SD4 2.75  $ Volume of Cell 101 in cm³")
    print()
    print("Explanation:")
    print("  - Range syntax: 50[2:4 3:5 0]")
    print("  - Tallies ALL pins from i=2 to 4, j=3 to 5 (9 pins total)")
    print("  - Can mix ranges and singles: [2:4 5 0] is valid")
    print("  - Visual selector makes this easy!")
    print()


def example_8_non_contiguous():
    """
    Example 8: Non-contiguous lattice selection (Method 2/3)
    Demonstrates union syntax for arbitrary lattice patterns
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Non-Contiguous Lattice Selection (NEW!)")
    print("=" * 70)
    print("\nScenario: Tally 4 corner pins of 10x10 lattice")
    print("  - Fuel pin (Cell 101) in Universe 5")
    print("  - Assembly (Cell 50) is LAT=1 (10x10 rectangular), in U=100")
    print("  - Select corners: (0,0,0), (9,9,0), (0,9,0), (9,0,0)")
    print("  - Core (Cell 1) fills U=100, is in Universe 0")
    print()

    wizard = MCNPWizard()

    wizard.target_cell = 101
    # Create non-contiguous selection with explicit element list
    corner_elements = [(0, 0, 0), (9, 9, 0), (0, 9, 0), (9, 0, 0)]
    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             lattice_spec=LatticeSpec(elements=corner_elements)),  # Non-contiguous!
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]

    path = wizard._build_tally_path()

    print("Generated Tally Specification (UNION SYNTAX - Method 2):")
    print(f"  F4:N {path}")
    print()
    print("⚠ WARNING: Requires SD card!")
    print("  Cell 101 is inside a lattice - volume must be specified")
    print("  SD4 2.75  $ Volume of Cell 101 in cm³")
    print()
    print("Explanation:")
    print("  - Non-contiguous selection detected (4 elements, but bounding box is 10x10=100)")
    print("  - Auto-generated union syntax: ( (path1) (path2) (path3) (path4) )")
    print("  - Each path explicitly lists one corner")
    print("  - MCNP tallies sum from all 4 corners only (not the 96 other elements!)")
    print()
    print("For SDEF with same pattern:")
    print("  SDEF CEL=d1 ERG=1.0")
    print("  SI1 L (101 < 50[0 0 0] < 1)")
    print("        (101 < 50[9 9 0] < 1)")
    print("        (101 < 50[0 9 0] < 1)")
    print("        (101 < 50[9 0 0] < 1)")
    print("  SP1 1 1 1 1  $ Equal probability for each corner")
    print()


def example_9_infinite_lattice():
    """
    Example 9: Infinite lattice with arbitrary indices (NEW!)
    Demonstrates FILL=N (simple fill) vs FILL= i:j k:l (bounded array)
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 9: Infinite Lattice (Simple Fill) - NEW!")
    print("=" * 70)
    print("\nScenario: Infinite lattice with sparse element selection")
    print("  - Fuel pin (Cell 101) in Universe 5")
    print("  - Assembly (Cell 50) is LAT=1 (rectangular), FILL=5 (SIMPLE FILL - infinite!)")
    print("  - Select 4 widely-spaced pins: (0,0,0), (100,200,0), (-50,-75,0), (25,-30,0)")
    print("  - Core (Cell 1) fills U=100, is in Universe 0")
    print()

    wizard = MCNPWizard()

    wizard.target_cell = 101
    # Infinite lattice: can use ANY indices (positive, negative, zero)
    sparse_elements = [(0, 0, 0), (100, 200, 0), (-50, -75, 0), (25, -30, 0)]
    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             is_infinite_lattice=True,  # NEW: marks as infinite
             lattice_spec=LatticeSpec(elements=sparse_elements)),
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]

    path = wizard._build_tally_path()

    print("Generated Tally Specification (INFINITE + UNION):")
    print(f"  F4:N {path}")
    print()
    print("⚠ WARNING: Requires SD card!")
    print("  Cell 101 is inside a lattice - volume must be specified")
    print("  SD4 2.75  $ Volume of Cell 101 in cm³")
    print()
    print("Explanation:")
    print("  - INFINITE lattice (FILL=5) allows ANY indices - no bounds!")
    print("  - Can use negative indices: (-50,-75,0) is perfectly valid")
    print("  - Can use huge indices: (100,200,0) works fine")
    print("  - Wizard auto-generates union syntax for sparse selection")
    print("  - Each path explicitly references one element")
    print()
    print("Key difference from bounded lattices:")
    print("  - BOUNDED: FILL= -5:5 -5:5 0:0 (explicit range, limited)")
    print("  - INFINITE: FILL=5 (simple fill, extends infinitely)")
    print()
    print("For SDEF in infinite lattice:")
    print("  SDEF CEL=d1 ERG=1.0")
    print("  SI1 L (101 < 50[0 0 0] < 1)")
    print("        (101 < 50[100 200 0] < 1)")
    print("        (101 < 50[-50 -75 0] < 1)")
    print("        (101 < 50[25 -30 0] < 1)")
    print("  SP1 1 1 1 1  $ Equal probability")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MCNP WIZARD - EXAMPLE DEMONSTRATIONS")
    print("=" * 70)
    print("\nThis script demonstrates what the wizard generates for")
    print("common MCNP universe and lattice scenarios.")

    example_1_simple_nested()
    example_2_lattice_simple()
    example_3_multilevel_lattice()
    example_4_sdef_generation()
    example_5_verification_deck()
    example_6_common_mistakes()
    example_7_lattice_ranges()  # NEW!
    example_8_non_contiguous()  # NEWEST!
    example_9_infinite_lattice()  # INFINITE LATTICES!

    print("\n" + "=" * 70)
    print("KEY TAKEAWAYS")
    print("=" * 70)
    print()
    print("1. Use < operator for 'contained in' relationships")
    print("2. Order is bottom-up (innermost cell first)")
    print("3. Lattice indices [i j k] immediately follow cell ID")
    print("4. Use spaces, not commas, in indices")
    print("5. Can use ranges: [i:j k:l m:n] to tally multiple elements")
    print("6. Non-contiguous selections use union syntax: ((path1)(path2)...)")
    print("7. Always use SD card when tallying in lattice elements")
    print("8. Test with PRINT 110 verification deck")
    print("9. For SDEF, use distribution method (SI/SP cards)")
    print("10. NEW: Visual selector auto-detects contiguous vs non-contiguous!")
    print("11. NEW: Infinite lattices (FILL=N) support arbitrary indices (±any value)")
    print("12. NEW: Bounded lattices (FILL= i:j...) restricted to explicit ranges")
    print()
    print("Run the interactive wizard with: python mcnp_wizard.py")
    print()


if __name__ == "__main__":
    main()
