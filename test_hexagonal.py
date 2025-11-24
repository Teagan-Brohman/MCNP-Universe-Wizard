#!/usr/bin/env python3
"""
Test script for hexagonal lattice visualization.
Demonstrates the new ASCII hexagon rendering feature.
"""

from mcnp_wizard import MCNPWizard, Node, LatticeSpec

def demo_hex_lattice():
    """
    Demonstrate hexagonal lattice with the visual selector.

    NOTE: This requires running the interactive wizard to see the full
    hexagonal ASCII art. The example below shows what code structure
    would be used for a LAT=2 (hexagonal) lattice.
    """
    print("=" * 70)
    print("HEXAGONAL LATTICE DEMONSTRATION")
    print("=" * 70)
    print()
    print("To test the hexagonal visual selector:")
    print("  1. Run: python mcnp_wizard.py")
    print("  2. Choose 'Tally' mode")
    print("  3. Enter target cell (e.g., 101)")
    print("  4. Enter parent cell (e.g., 50)")
    print("  5. Answer 'y' to 'Is it a lattice?'")
    print("  6. Choose '2' for Hexagonal (LAT=2)")
    print("  7. Choose fill type and bounds")
    print("  8. Select 'Use visual selector'")
    print()
    print("In the visual selector for hexagonal lattices, you'll see:")
    print()
    print("Compact hexagonal format:")
    print("     0   1   2   3   4")
    print("   0  ·   ·   X   ·   ·")
    print("     1  ·   X   X   X   ·")
    print("   2  X   X   ·   X   X")
    print()
    print("Features:")
    print("  - Single-character cells (·=unselected, X=selected)")
    print("  - Odd rows shifted right to show hexagonal adjacency")
    print("  - Column headers (i-indices) aligned with cells below")
    print("  - Row labels (j-indices) on the left")
    print()
    print("Navigation in hexagonal mode:")
    print("  - Arrow Keys: Move in 6 directions (hex neighbors)")
    print("  - UP: Move to hex above-left (NW)")
    print("  - DOWN: Move to hex below-right (SE)")
    print("  - LEFT/RIGHT: Move horizontally (W/E)")
    print("  - W/E/Z/X: Additional diagonal controls")
    print("  - Space: Toggle cell selection")
    print("  - [/]: Change k-layer")
    print("  - d: Done (generate spec)")
    print()
    print("Hexagonal coordinate system:")
    print("  - Uses offset coordinates (odd rows shifted right)")
    print("  - Each hex has 6 neighbors (unlike rectangular's 4)")
    print("  - Properly handles MCNP LAT=2 indexing")
    print()

    # Example: Create a hexagonal lattice node programmatically
    wizard = MCNPWizard()
    wizard.target_cell = 101

    # Select a few hexagonal cells manually
    hex_elements = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]

    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             lattice_type=2,  # LAT=2 = hexagonal
             lattice_spec=LatticeSpec(elements=hex_elements)),
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]

    path = wizard._build_tally_path()

    print("Example output for hexagonal lattice selection:")
    print(f"  F4:N {path}")
    print()
    print("Key features of hexagonal lattices in this wizard:")
    print("  ✅ Compact single-character display format")
    print("  ✅ Proper column and row alignment")
    print("  ✅ 6-direction navigation matching hex geometry")
    print("  ✅ Offset coordinate system (matches MCNP LAT=2)")
    print("  ✅ Visual indication of cursor and selected cells")
    print("  ✅ Supports contiguous and non-contiguous selections")
    print("  ✅ Works with infinite and bounded lattices")
    print("  ✅ Odd rows shifted to show hexagonal adjacency pattern")
    print()


if __name__ == "__main__":
    demo_hex_lattice()
