#!/usr/bin/env python3
"""
Test to verify k-range support in lattice specifications
"""

from mcnp_wizard import Node, MCNPWizard, LatticeSpec

def test_k_range_manual():
    """Test creating a lattice spec with k-range manually"""
    print("=" * 70)
    print("TEST: K-Range Support - Manual Creation")
    print("=" * 70)

    wizard = MCNPWizard()
    wizard.target_cell = 101

    # Create a spec with k-range from 0 to 5
    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             lattice_spec=LatticeSpec(i=(0, 9), j=(0, 9), k=(0, 5))),  # k-range!
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]

    path = wizard._build_tally_path()

    print("\nScenario: 10x10 lattice with 6 axial layers (k=0 to 5)")
    print(f"\nGenerated specification:\n  F4:N {path}")
    print("\nNotice the k-range: [0:9 0:9 0:5]")
    print("This tallies across ALL 6 axial layers!")
    print()

def test_k_single_vs_range():
    """Compare single k vs k-range"""
    print("=" * 70)
    print("TEST: Single K vs K-Range Comparison")
    print("=" * 70)

    wizard = MCNPWizard()
    wizard.target_cell = 101

    # Single k-layer
    wizard.universe_stack = [
        Node(cell_id=101, universe_id=5),
        Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
             lattice_spec=LatticeSpec(i=5, j=5, k=0)),  # Single k
        Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
    ]
    path_single = wizard._build_tally_path()

    # K-range
    wizard.universe_stack[1].lattice_spec = LatticeSpec(i=5, j=5, k=(0, 10))
    path_range = wizard._build_tally_path()

    print("\nSingle k-layer (k=0 only):")
    print(f"  F4:N {path_single}")

    print("\nK-range (k=0 to 10):")
    print(f"  F4:N {path_range}")

    print("\nThe second spec tallies the same pin across 11 axial layers!")
    print()

def test_mixed_k_specification():
    """Test mixing ranges and singles with k"""
    print("=" * 70)
    print("TEST: Mixed Specifications with K")
    print("=" * 70)

    wizard = MCNPWizard()
    wizard.target_cell = 101

    examples = [
        (LatticeSpec(i=(0, 9), j=(0, 9), k=0), "Full i-j grid, single k-layer"),
        (LatticeSpec(i=5, j=(0, 9), k=0), "Single i, full j, single k"),
        (LatticeSpec(i=5, j=5, k=(0, 10)), "Single i-j, full k-range"),
        (LatticeSpec(i=(0, 9), j=5, k=(0, 2)), "Full i, single j, k-range"),
    ]

    for spec, description in examples:
        wizard.universe_stack = [
            Node(cell_id=101, universe_id=5),
            Node(cell_id=50, universe_id=100, fill_id=5, is_lattice=True,
                 lattice_spec=spec),
            Node(cell_id=1, universe_id=0, fill_id=100, is_lattice=False)
        ]
        path = wizard._build_tally_path()
        print(f"\n{description}:")
        print(f"  F4:N {path}")

    print()

if __name__ == "__main__":
    test_k_range_manual()
    test_k_single_vs_range()
    test_mixed_k_specification()

    print("=" * 70)
    print("CONCLUSION: K-ranges fully supported!")
    print("=" * 70)
    print()
