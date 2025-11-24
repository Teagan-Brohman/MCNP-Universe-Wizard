#!/usr/bin/env python3
"""
MCNP Universe & Lattice Wizard
A tool to generate proper universe specifications for MCNP tallies and source definitions.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List, Union
import numpy as np
import curses


@dataclass
class LatticeSpec:
    """
    Represents lattice index specification (supports both contiguous and non-contiguous).

    Two modes:
    1. Contiguous (ranges): Use i/j/k fields with int or (min, max) tuples
    2. Non-contiguous (discrete): Use elements field with list of (i,j,k) tuples
    """
    # For contiguous ranges (original functionality)
    i: Optional[Union[int, Tuple[int, int]]] = None
    j: Optional[Union[int, Tuple[int, int]]] = None
    k: Optional[Union[int, Tuple[int, int]]] = None

    # For non-contiguous discrete elements (new functionality)
    elements: Optional[List[Tuple[int, int, int]]] = None

    def is_contiguous(self) -> bool:
        """Check if this represents a contiguous range (vs discrete elements)"""
        return self.elements is None

    def is_non_contiguous(self) -> bool:
        """Check if this represents discrete non-contiguous elements"""
        return self.elements is not None

    def format_dimension(self, val: Union[int, Tuple[int, int]]) -> str:
        """Format a single dimension as either 'n' or 'min:max'"""
        if isinstance(val, tuple):
            return f"{val[0]}:{val[1]}"
        return str(val)

    def to_mcnp_string(self) -> str:
        """
        Convert to MCNP lattice index format.
        Contiguous: [i j k] or [i:i2 j:j2 k:k2]
        Non-contiguous: Returns first element (use get_all_elements() for full list)
        """
        if self.is_contiguous():
            i_str = self.format_dimension(self.i)
            j_str = self.format_dimension(self.j)
            k_str = self.format_dimension(self.k)
            return f"[{i_str} {j_str} {k_str}]"
        else:
            # For non-contiguous, return representation of first element
            if self.elements:
                i, j, k = self.elements[0]
                return f"[{i} {j} {k}] (+{len(self.elements)-1} more)"
            return "[empty]"

    def to_mcnp_single_index(self, element: Tuple[int, int, int]) -> str:
        """Format a single (i,j,k) tuple as MCNP index"""
        return f"[{element[0]} {element[1]} {element[2]}]"

    def get_all_elements(self) -> List[Tuple[int, int, int]]:
        """Get list of all (i,j,k) tuples, whether contiguous or non-contiguous"""
        if self.is_non_contiguous():
            return self.elements
        else:
            # For contiguous, return single element or None (will be handled differently)
            return []

    def is_single_element(self) -> bool:
        """Check if this is a single element (no ranges, or one discrete element)"""
        if self.is_contiguous():
            return all(isinstance(v, int) for v in [self.i, self.j, self.k])
        else:
            return len(self.elements) == 1

    def element_count(self) -> int:
        """Return number of discrete lattice elements represented"""
        if self.is_non_contiguous():
            return len(self.elements)
        else:
            # Calculate size of contiguous range
            def get_size(val):
                if isinstance(val, tuple):
                    return val[1] - val[0] + 1
                return 1
            return get_size(self.i) * get_size(self.j) * get_size(self.k)

    def __repr__(self):
        if self.is_contiguous():
            return self.to_mcnp_string()
        else:
            return f"NonContiguous[{len(self.elements)} elements]"


@dataclass
class Node:
    """
    Represents a single cell in the universe stack path.
    """
    cell_id: int
    universe_id: Optional[int] = None  # Universe this cell belongs to
    fill_id: Optional[int] = None      # Universe that fills this cell
    is_lattice: bool = False
    is_infinite_lattice: bool = False  # True for simple fill (FILL=N), False for fully specified
    lattice_spec: Optional[LatticeSpec] = None  # New: supports ranges
    lattice_type: Optional[int] = None  # 1=rectangular, 2=hexagonal
    lattice_bounds: Optional[Tuple[Tuple[int,int], Tuple[int,int], Tuple[int,int]]] = None  # For bounded: actual. For infinite: viewing window
    transform: Optional[np.ndarray] = None  # For future SDEF position calculation

    # Legacy support for old single-index format
    @property
    def lattice_index(self) -> Optional[Tuple[int, int, int]]:
        """Backward compatibility: return single index if lattice_spec is single element"""
        if self.lattice_spec and self.lattice_spec.is_single_element():
            return (self.lattice_spec.i, self.lattice_spec.j, self.lattice_spec.k)
        return None

    def __repr__(self):
        lat_str = f" [LAT spec: {self.lattice_spec}]" if self.lattice_spec else ""
        fill_str = f" (fills U={self.fill_id})" if self.fill_id else ""
        return f"Cell {self.cell_id} in U={self.universe_id}{lat_str}{fill_str}"


class MCNPWizard:
    """
    Interactive wizard for generating MCNP universe specifications.
    """
    
    def __init__(self):
        self.universe_stack: List[Node] = []
        self.target_cell: Optional[int] = None
        self.target_volume: Optional[float] = None
        
    def run(self):
        """Main entry point for the wizard."""
        print("=" * 70)
        print("MCNP Universe & Lattice Specification Wizard")
        print("=" * 70)
        print("\nThis wizard will help you generate proper universe specifications")
        print("for MCNP tallies (F-cards) and source definitions (SDEF).\n")
        
        # Choose mode
        mode = self._choose_mode()
        
        # Build the universe stack
        self._build_universe_stack()
        
        # Generate output based on mode
        if mode == 'tally':
            self._generate_tally_output()
        elif mode == 'sdef':
            self._generate_sdef_output()
        else:
            self._generate_both_outputs()
            
        # Offer verification
        self._offer_verification()
        
    def _choose_mode(self) -> str:
        """Ask user what type of specification they need."""
        print("What do you need to generate?")
        print("  1. Tally specification (F4, F7, etc.)")
        print("  2. Source definition (SDEF)")
        print("  3. Both")
        
        while True:
            choice = input("\nEnter choice (1/2/3): ").strip()
            if choice == '1':
                return 'tally'
            elif choice == '2':
                return 'sdef'
            elif choice == '3':
                return 'both'
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    def _build_universe_stack(self):
        """Build the universe stack by prompting user bottom-up."""
        print("\n" + "=" * 70)
        print("Building Universe Stack (Bottom-Up)")
        print("=" * 70)
        
        # Get target cell
        self.target_cell = self._get_int_input(
            "\n[TARGET CELL]\nWhat is the specific cell ID you want to tally/source?"
        )
        
        # Create target node
        current_node = Node(cell_id=self.target_cell)
        
        # Ask if target is in a universe
        in_universe = self._get_yes_no(
            f"\nIs Cell {self.target_cell} inside a universe (not Universe 0)?"
        )
        
        if in_universe:
            current_node.universe_id = self._get_int_input(
                f"What universe number is Cell {self.target_cell} in?"
            )
        else:
            current_node.universe_id = 0
            self.universe_stack.append(current_node)
            print(f"\n✓ Cell {self.target_cell} is in the global universe (U=0)")
            return
        
        self.universe_stack.append(current_node)
        
        # Now climb up the stack
        self._climb_universe_stack(current_node.universe_id)
        
        print("\n" + "=" * 70)
        print("Universe Stack Complete:")
        print("=" * 70)
        for i, node in enumerate(self.universe_stack):
            print(f"  Level {i}: {node}")
        print()
        
    def _climb_universe_stack(self, current_universe: int):
        """Recursively climb up the universe hierarchy."""
        if current_universe == 0:
            return
            
        # Ask what cell fills this universe
        print(f"\n[PARENT CELL for U={current_universe}]")
        parent_cell = self._get_int_input(
            f"What cell FILLS universe {current_universe}?"
        )
        
        parent_node = Node(
            cell_id=parent_cell,
            fill_id=current_universe
        )
        
        # Check if it's a lattice
        is_lattice = self._get_yes_no(
            f"\nIs Cell {parent_cell} a lattice (LAT=1 or LAT=2)?"
        )
        
        parent_node.is_lattice = is_lattice

        if is_lattice:
            print(f"\n[LATTICE SPECIFICATION for Cell {parent_cell}]")

            # Get lattice type
            print("\nLattice type:")
            print("  1 = Rectangular (LAT=1)")
            print("  2 = Hexagonal (LAT=2)")
            lattice_type = self._get_int_input("Enter lattice type (1 or 2):")
            parent_node.lattice_type = lattice_type

            # NEW: Ask about fill type (infinite vs bounded)
            print("\nFILL card type:")
            print("  1 = Simple fill (FILL=N) - lattice extends infinitely")
            print("  2 = Fully specified (FILL= i_min:i_max j_min:j_max k_min:k_max ...) - bounded")
            print("\nCheck your MCNP input:")
            print("  Simple example: '50 1 -1.0 -1 LAT=2 FILL=5 U=100'")
            print("  Bounded example: '50 1 -1.0 -1 LAT=2 FILL= -5:5 -4:4 0:2 10 999r U=100'")
            fill_type = self._get_int_input("Enter FILL type (1 or 2):")

            if fill_type == 1:
                # INFINITE LATTICE (simple fill)
                parent_node.is_infinite_lattice = True
                print("\n⚠ INFINITE LATTICE detected (simple fill).")
                print("   Your lattice extends infinitely - you can reference ANY indices!")
                print("   Example: [0 0 0], [9999 -500 0], etc.")

                use_visual = self._get_yes_no("\nUse visual selector? (requires defining a viewing window)")

                if use_visual:
                    # Get viewing window for visualization
                    print("\n[VIEWING WINDOW for Visual Selector]")
                    print("These are NOT actual lattice bounds (lattice is infinite).")
                    print("Just specify what range you want to SEE in the visual selector.")
                    print("\nRecommended: Keep small (<20x20) for usable display.")
                    i_min = self._get_int_input("  Viewing i minimum:")
                    i_max = self._get_int_input("  Viewing i maximum:")
                    j_min = self._get_int_input("  Viewing j minimum:")
                    j_max = self._get_int_input("  Viewing j maximum:")
                    k_min = self._get_int_input("  Viewing k minimum:")
                    k_max = self._get_int_input("  Viewing k maximum:")

                    bounds = ((i_min, i_max), (j_min, j_max), (k_min, k_max))
                    parent_node.lattice_bounds = bounds  # Viewing window only!

                    # Validate size before launching
                    if self._validate_visual_selector_size(bounds):
                        lattice_spec = self._launch_visual_selector(lattice_type, bounds, is_infinite=True)
                        if lattice_spec:
                            parent_node.lattice_spec = lattice_spec
                        else:
                            print("Visual selection cancelled. Falling back to manual entry.")
                            parent_node.lattice_spec = self._manual_lattice_entry(is_infinite=True)
                    else:
                        print("Falling back to manual entry.")
                        parent_node.lattice_spec = self._manual_lattice_entry(is_infinite=True)
                else:
                    # Manual entry for infinite lattice
                    parent_node.lattice_bounds = None  # No bounds!
                    parent_node.lattice_spec = self._manual_lattice_entry(is_infinite=True)

            else:
                # BOUNDED LATTICE (fully specified fill)
                parent_node.is_infinite_lattice = False

                # Get actual lattice bounds
                print("\nLattice dimensions (from your FILL card):")
                print("Example: If FILL card says -5:5 -4:4 0:2, enter those values")
                i_min = self._get_int_input("  i minimum:")
                i_max = self._get_int_input("  i maximum:")
                j_min = self._get_int_input("  j minimum:")
                j_max = self._get_int_input("  j maximum:")
                k_min = self._get_int_input("  k minimum:")
                k_max = self._get_int_input("  k maximum:")

                bounds = ((i_min, i_max), (j_min, j_max), (k_min, k_max))
                parent_node.lattice_bounds = bounds

                # Choose selection method
                print("\nHow would you like to specify which lattice elements to tally?")
                print("  1 = Visual selector (interactive grid)")
                print("  2 = Manual entry (type indices/ranges)")
                selection_method = self._get_int_input("Enter choice (1 or 2):")

                if selection_method == 1:
                    # Validate size before launching
                    if self._validate_visual_selector_size(bounds):
                        lattice_spec = self._launch_visual_selector(lattice_type, bounds, is_infinite=False)
                        if lattice_spec:
                            parent_node.lattice_spec = lattice_spec
                        else:
                            print("Visual selection cancelled. Falling back to manual entry.")
                            parent_node.lattice_spec = self._manual_lattice_entry(is_infinite=False)
                    else:
                        print("Falling back to manual entry.")
                        parent_node.lattice_spec = self._manual_lattice_entry(is_infinite=False)
                else:
                    # Manual entry
                    parent_node.lattice_spec = self._manual_lattice_entry(is_infinite=False)
        
        # Ask what universe the parent is in
        parent_in_universe = self._get_yes_no(
            f"\nIs Cell {parent_cell} inside a universe (not Universe 0)?"
        )
        
        if parent_in_universe:
            parent_node.universe_id = self._get_int_input(
                f"What universe number is Cell {parent_cell} in?"
            )
        else:
            parent_node.universe_id = 0
            
        self.universe_stack.append(parent_node)
        
        # Recurse if not at global level
        if parent_node.universe_id != 0:
            self._climb_universe_stack(parent_node.universe_id)
    
    def _generate_tally_output(self):
        """Generate the tally specification string."""
        print("\n" + "=" * 70)
        print("TALLY SPECIFICATION")
        print("=" * 70)
        
        # Ask for tally type
        tally_type = input("\nEnter tally type (e.g., F4:N, F7:N, F4:P): ").strip().upper()
        
        # Build the path string
        path_string = self._build_tally_path()
        
        # Generate tally card
        tally_card = f"{tally_type} {path_string}"
        
        print("\n" + "-" * 70)
        print("GENERATED TALLY CARD:")
        print("-" * 70)
        print(tally_card)
        print("-" * 70)
        
        # Check if SD card is needed
        needs_sd = self._check_needs_sd_card()
        
        if needs_sd:
            print("\n⚠ WARNING: This tally requires a Segment Divisor (SD) card!")
            print(f"   Target Cell {self.target_cell} is inside a lattice.")
            print("   MCNP cannot auto-calculate volumes for lattice elements.")
            print(f"   You must specify the volume of Cell {self.target_cell} in cm³.")

            provide_volume = self._get_yes_no(f"\nDo you know the volume of Cell {self.target_cell} (in cm³)?")

            if provide_volume:
                self.target_volume = self._get_float_input(f"Enter volume of Cell {self.target_cell} (cm³):")
                tally_num = tally_type[1]  # Extract number from F4:N -> 4
                sd_card = f"SD{tally_num} {self.target_volume}"
                print("\n" + "-" * 70)
                print("REQUIRED SD CARD:")
                print("-" * 70)
                print(sd_card)
                print("-" * 70)
                print(f"\nThis specifies that Cell {self.target_cell} has a volume of {self.target_volume} cm³")
                print("in each lattice element where it appears.")
            else:
                print("\n⚠ You MUST add an SD card manually with the correct volume!")
                print(f"   Format: SD{tally_type[1]} <volume_of_cell_{self.target_cell}_in_cm3>")
                print(f"   Example: SD{tally_type[1]} 2.75  $ Volume of Cell {self.target_cell} in cm³")
        
    def _generate_sdef_output(self):
        """Generate the SDEF specification using distribution method."""
        print("\n" + "=" * 70)
        print("SOURCE DEFINITION (SDEF) SPECIFICATION")
        print("=" * 70)

        print("\nUsing the robust Distribution method (SI/SP cards)...")

        # Ask for distribution number
        dist_num = self._get_int_input("\nEnter distribution number to use (e.g., 1 for d1):", default=1)

        # Generate SDEF card
        sdef_card = f"SDEF CEL=d{dist_num}"

        # Ask for position
        include_pos = self._get_yes_no("\nDo you want to specify a position (POS)?")

        if include_pos:
            print("\n⚠ NOTE: You must specify coordinates in the TARGET cell's local frame.")
            print("   (Global coordinate transformation not yet implemented)")
            x = self._get_float_input("  X coordinate:")
            y = self._get_float_input("  Y coordinate:")
            z = self._get_float_input("  Z coordinate:")
            sdef_card += f" POS={x} {y} {z}"

        # Ask for other parameters
        include_erg = self._get_yes_no("\nDo you want to specify energy (ERG)?")
        if include_erg:
            erg = self._get_float_input("  Energy (MeV):")
            sdef_card += f" ERG={erg}"

        # Generate SI/SP cards based on contiguity
        if self._has_non_contiguous_lattice():
            # NON-CONTIGUOUS: Use Method 3 (separate paths in SI list)
            # Find the non-contiguous lattice node
            non_contiguous_node = None
            for node in self.universe_stack:
                if node.is_lattice and node.lattice_spec and node.lattice_spec.is_non_contiguous():
                    non_contiguous_node = node
                    break

            elements = non_contiguous_node.lattice_spec.get_all_elements()
            num_elements = len(elements)

            # Build separate paths for each element
            paths = []
            for element in elements:
                single_path = self._build_single_path(lattice_element=element)
                paths.append(f"({single_path})")

            # SI card with list of paths
            si_card = f"SI{dist_num} L"
            for path in paths:
                si_card += f" {path}"

            # SP card with equal probabilities
            sp_values = " ".join(["1"] * num_elements)
            sp_card = f"SP{dist_num} {sp_values}"

            print(f"\n⚠ NON-CONTIGUOUS selection detected!")
            print(f"   Generating {num_elements} separate source locations with equal probability.")

        else:
            # CONTIGUOUS: Use simple distribution (original behavior)
            path_string = self._build_tally_path()
            si_card = f"SI{dist_num} L {path_string}"
            sp_card = f"SP{dist_num} 1"

        print("\n" + "-" * 70)
        print("GENERATED SOURCE DEFINITION:")
        print("-" * 70)
        print(sdef_card)
        print(si_card)
        print(sp_card)
        print("-" * 70)
        
    def _generate_both_outputs(self):
        """Generate both tally and SDEF specifications."""
        self._generate_tally_output()
        self._generate_sdef_output()

    def _has_non_contiguous_lattice(self) -> bool:
        """Check if any lattice in the universe stack is non-contiguous"""
        for node in self.universe_stack:
            if node.is_lattice and node.lattice_spec and node.lattice_spec.is_non_contiguous():
                return True
        return False

    def _build_single_path(self, lattice_element: Optional[Tuple[int, int, int]] = None) -> str:
        """
        Build a single path through the universe hierarchy.

        Args:
            lattice_element: If provided, use this specific (i,j,k) for the non-contiguous lattice

        Returns:
            Path string like "target < parent[i j k] < global"
        """
        parts = [str(self.universe_stack[0].cell_id)]

        for node in self.universe_stack[1:]:
            if node.is_lattice and node.lattice_spec:
                if node.lattice_spec.is_non_contiguous() and lattice_element is not None:
                    # Use specific element for this node
                    parts.append(f"{node.cell_id}{node.lattice_spec.to_mcnp_single_index(lattice_element)}")
                elif node.lattice_spec.is_contiguous():
                    # Use range syntax
                    parts.append(f"{node.cell_id}{node.lattice_spec.to_mcnp_string()}")
                else:
                    # Non-contiguous but no element specified - shouldn't happen
                    parts.append(f"{node.cell_id}")
            else:
                parts.append(str(node.cell_id))

        return " < ".join(parts)

    def _build_union_paths(self) -> str:
        """
        Build union of paths for non-contiguous lattice selections.
        Uses MCNP Method 2: ( (path1) (path2) ... (pathN) )
        """
        # Find the non-contiguous lattice node
        non_contiguous_node = None
        for node in self.universe_stack:
            if node.is_lattice and node.lattice_spec and node.lattice_spec.is_non_contiguous():
                non_contiguous_node = node
                break

        if not non_contiguous_node:
            # Shouldn't happen, but fall back to regular path
            return self._build_single_path()

        # Get all elements from the non-contiguous lattice
        elements = non_contiguous_node.lattice_spec.get_all_elements()

        # Build a separate path for each element
        paths = []
        for element in elements:
            single_path = self._build_single_path(lattice_element=element)
            paths.append(f"( {single_path} )")

        # Join with spaces (union syntax)
        union = " ".join(paths)

        return f"( {union} )"

    def _build_tally_path(self) -> str:
        """
        Build the path string in the format: ( Target < Parent[i j k] < Global )
        Bottom-up ordering (innermost first).

        Supports:
        - Single indices: [5 3 0]
        - Contiguous ranges: [0:9 0:9 0:2]
        - Non-contiguous (Method 2 union): ( (path1) (path2) ... )
        """
        if not self.universe_stack:
            return f"( {self.target_cell} )"

        # Check if we have any non-contiguous lattices
        if self._has_non_contiguous_lattice():
            return self._build_union_paths()

        # Contiguous case (original behavior)
        path = self._build_single_path()
        return f"( {path} )"
    
    def _check_needs_sd_card(self) -> bool:
        """Check if this specification needs an SD card."""
        # SD card needed if target is inside a lattice
        if len(self.universe_stack) > 1:
            for node in self.universe_stack[1:]:
                if node.is_lattice:
                    return True
        return False
    
    def _offer_verification(self):
        """Offer to generate verification input."""
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)
        
        generate_verify = self._get_yes_no(
            "\nWould you like to generate a verification deck snippet?"
        )
        
        if not generate_verify:
            print("\n✓ Wizard complete!")
            return
        
        self._generate_verification_deck()
    
    def _generate_verification_deck(self):
        """Generate a verification deck snippet."""
        print("\n" + "-" * 70)
        print("VERIFICATION DECK SNIPPET")
        print("-" * 70)
        print("C --- Paste this into an MCNP input for verification ---")
        print("C --- Run with 50 particles and check PRINT 110 output ---")
        print()
        
        path_string = self._build_tally_path()
        
        print(f"SDEF CEL=d1 ERG=1.0")
        print(f"SI1 L {path_string}")
        print(f"SP1 1")
        print(f"C")
        print(f"NPS 50")
        print(f"PRINT 110")
        print(f"C")
        print(f"C Set all materials to VOID for testing:")
        print(f"C M0   $ Void")
        print()
        print("-" * 70)
        print("\n✓ Instructions:")
        print("  1. Add this to a copy of your input deck")
        print("  2. Set all materials to void (M0 or remove material cards)")
        print("  3. Run MCNP")
        print("  4. Check output file for 'source particle' lines")
        print("  5. Verify particles start in the correct cell/lattice position")
        print("  6. If particles are 'lost' or in Cell 0, check your specification")

    def _validate_visual_selector_size(self, bounds: Tuple[Tuple[int,int], Tuple[int,int], Tuple[int,int]]) -> bool:
        """
        Check if visual selector can handle this size.
        Warns if grid is too large for comfortable terminal display.
        """
        i_range, j_range, k_range = bounds
        i_size = i_range[1] - i_range[0] + 1
        j_size = j_range[1] - j_range[0] + 1
        k_size = k_range[1] - k_range[0] + 1

        cells_per_layer = i_size * j_size
        total_cells = cells_per_layer * k_size

        MAX_CELLS_PER_LAYER = 400  # 20x20 is reasonable
        MAX_TOTAL_CELLS = 2000      # Warn if very large

        if cells_per_layer > MAX_CELLS_PER_LAYER:
            print(f"\n⚠ WARNING: Grid is {i_size}x{j_size} = {cells_per_layer} cells per layer!")
            print(f"   Visual selector works best with grids smaller than 20x20 (~400 cells).")
            print(f"   Large grids may not fit in your terminal or be hard to navigate.")
            return self._get_yes_no("Continue with visual selector anyway?")

        if total_cells > MAX_TOTAL_CELLS:
            print(f"\n⚠ WARNING: Total lattice has {total_cells} cells across {k_size} layers!")
            print(f"   This may be slow or difficult to use.")
            return self._get_yes_no("Continue with visual selector anyway?")

        return True

    def _launch_visual_selector(self, lattice_type: int, bounds: Tuple[Tuple[int,int], Tuple[int,int], Tuple[int,int]], is_infinite: bool = False) -> Optional[LatticeSpec]:
        """Launch the curses-based visual lattice selector."""
        print("\nLaunching visual lattice selector...")
        if is_infinite:
            print("(Viewing window mode - lattice is actually infinite)")
        print("(Terminal will switch to interactive mode)")
        input("Press Enter to continue...")

        try:
            selector = VisualLatticeSelector(lattice_type, bounds, is_infinite=is_infinite)
            result = curses.wrapper(selector.run)
            return result
        except Exception as e:
            print(f"\nError in visual selector: {e}")
            return None

    def _manual_lattice_entry(self, is_infinite: bool = False) -> LatticeSpec:
        """Manual entry of lattice specification (supports ranges)."""
        print("\nManual lattice element specification:")

        if is_infinite:
            print("⚠ Note: This is an INFINITE lattice (simple fill).")
            print("   You can enter ANY indices (positive, negative, or zero).")
            print("   The lattice extends infinitely in all directions.")

        print("For each dimension, enter either:")
        print("  - A single index (e.g., 5)")
        print("  - A range as 'min:max' (e.g., 0:9)")
        print()

        def parse_dimension(prompt: str) -> Union[int, Tuple[int, int]]:
            """Parse a single dimension (can be single value or range)."""
            while True:
                response = input(prompt).strip()
                if ':' in response:
                    # Range format
                    try:
                        parts = response.split(':')
                        if len(parts) != 2:
                            print("  Invalid range format. Use 'min:max' (e.g., 0:9)")
                            continue
                        min_val = int(parts[0].strip())
                        max_val = int(parts[1].strip())
                        if min_val > max_val:
                            print("  Minimum must be <= maximum")
                            continue
                        return (min_val, max_val)
                    except ValueError:
                        print("  Invalid numbers in range. Try again.")
                        continue
                else:
                    # Single value
                    try:
                        return int(response)
                    except ValueError:
                        print("  Invalid input. Enter a number or range (min:max)")
                        continue

        i_spec = parse_dimension("  i index or range (e.g., 5 or 0:9): ")
        j_spec = parse_dimension("  j index or range (e.g., 5 or 0:9): ")
        k_spec = parse_dimension("  k index or range (e.g., 0 or 0:2): ")

        return LatticeSpec(i=i_spec, j=j_spec, k=k_spec)

    # Helper input methods
    def _get_int_input(self, prompt: str, default: Optional[int] = None) -> int:
        """Get integer input from user with validation."""
        while True:
            try:
                if default is not None:
                    response = input(f"{prompt} [default: {default}]: ").strip()
                    if not response:
                        return default
                else:
                    response = input(f"{prompt}: ").strip()
                
                return int(response)
            except ValueError:
                print("Invalid input. Please enter an integer.")
    
    def _get_float_input(self, prompt: str) -> float:
        """Get float input from user with validation."""
        while True:
            try:
                response = input(f"{prompt}: ").strip()
                return float(response)
            except ValueError:
                print("Invalid input. Please enter a number.")
    
    def _get_yes_no(self, prompt: str) -> bool:
        """Get yes/no input from user."""
        while True:
            response = input(f"{prompt} (y/n): ").strip().lower()
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")


class VisualLatticeSelector:
    """
    Curses-based visual lattice selector for choosing lattice elements.
    """

    def __init__(self, lattice_type: int, bounds: Tuple[Tuple[int,int], Tuple[int,int], Tuple[int,int]], is_infinite: bool = False):
        """
        Initialize the visual selector.

        Args:
            lattice_type: 1 for rectangular, 2 for hexagonal
            bounds: ((i_min, i_max), (j_min, j_max), (k_min, k_max))
            is_infinite: True if this is an infinite lattice (bounds are viewing window only)
        """
        self.lattice_type = lattice_type
        self.is_infinite = is_infinite
        self.i_bounds, self.j_bounds, self.k_bounds = bounds
        self.current_k = (self.k_bounds[0] + self.k_bounds[1]) // 2  # Start at middle k-layer
        self.cursor_i = (self.i_bounds[0] + self.i_bounds[1]) // 2
        self.cursor_j = (self.j_bounds[0] + self.j_bounds[1]) // 2
        self.selected = set()  # Set of (i, j, k) tuples

    def _get_hex_neighbor(self, i, j, direction):
        """
        Get the neighbor coordinates for a hexagonal lattice cell.
        Uses offset coordinate system (odd rows shifted right).

        Args:
            i, j: Current cell coordinates
            direction: 'E', 'W', 'NE', 'NW', 'SE', 'SW'

        Returns:
            (new_i, new_j) tuple
        """
        is_odd_row = (j % 2 == 1)

        if direction == 'E':
            return (i + 1, j)
        elif direction == 'W':
            return (i - 1, j)
        elif direction == 'NE':
            if is_odd_row:
                return (i + 1, j - 1)
            else:
                return (i, j - 1)
        elif direction == 'NW':
            if is_odd_row:
                return (i, j - 1)
            else:
                return (i - 1, j - 1)
        elif direction == 'SE':
            if is_odd_row:
                return (i + 1, j + 1)
            else:
                return (i, j + 1)
        elif direction == 'SW':
            if is_odd_row:
                return (i, j + 1)
            else:
                return (i - 1, j + 1)
        else:
            return (i, j)

    def run(self, stdscr) -> Optional[LatticeSpec]:
        """Main curses loop for lattice selection."""
        curses.curs_set(0)  # Hide cursor
        stdscr.clear()

        while True:
            stdscr.clear()
            self._draw_interface(stdscr)
            stdscr.refresh()

            key = stdscr.getch()

            if key == ord('q') or key == 27:  # q or ESC
                return None
            elif key == ord('\n') or key == ord(' '):  # Enter or Space to toggle
                cell = (self.cursor_i, self.cursor_j, self.current_k)
                if cell in self.selected:
                    self.selected.remove(cell)
                else:
                    self.selected.add(cell)
            elif key == ord('d'):  # Done
                if self.selected:
                    return self._create_lattice_spec()
                else:
                    stdscr.addstr(0, 0, "ERROR: No cells selected! Press any key...", curses.A_REVERSE)
                    stdscr.refresh()
                    stdscr.getch()
            elif key == curses.KEY_UP:
                if self.lattice_type == 2:  # Hexagonal - move NW
                    new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'NW')
                    if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                        self.cursor_i, self.cursor_j = new_i, new_j
                else:  # Rectangular
                    self.cursor_j = max(self.j_bounds[0], self.cursor_j - 1)
            elif key == curses.KEY_DOWN:
                if self.lattice_type == 2:  # Hexagonal - move SE
                    new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'SE')
                    if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                        self.cursor_i, self.cursor_j = new_i, new_j
                else:  # Rectangular
                    self.cursor_j = min(self.j_bounds[1], self.cursor_j + 1)
            elif key == curses.KEY_LEFT:
                if self.lattice_type == 2:  # Hexagonal - move W
                    new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'W')
                    if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                        self.cursor_i, self.cursor_j = new_i, new_j
                else:  # Rectangular
                    self.cursor_i = max(self.i_bounds[0], self.cursor_i - 1)
            elif key == curses.KEY_RIGHT:
                if self.lattice_type == 2:  # Hexagonal - move E
                    new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'E')
                    if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                        self.cursor_i, self.cursor_j = new_i, new_j
                else:  # Rectangular
                    self.cursor_i = min(self.i_bounds[1], self.cursor_i + 1)
            # Additional hex navigation keys (Q/E for NE/NW diagonals, Z/X for SW/SE diagonals)
            elif key == ord('e') and self.lattice_type == 2:  # NE diagonal
                new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'NE')
                if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                    self.cursor_i, self.cursor_j = new_i, new_j
            elif key == ord('w') and self.lattice_type == 2:  # NW diagonal (duplicate of UP, but explicit)
                new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'NW')
                if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                    self.cursor_i, self.cursor_j = new_i, new_j
            elif key == ord('x') and self.lattice_type == 2:  # SE diagonal (duplicate of DOWN, but explicit)
                new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'SE')
                if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                    self.cursor_i, self.cursor_j = new_i, new_j
            elif key == ord('z') and self.lattice_type == 2:  # SW diagonal
                new_i, new_j = self._get_hex_neighbor(self.cursor_i, self.cursor_j, 'SW')
                if self.i_bounds[0] <= new_i <= self.i_bounds[1] and self.j_bounds[0] <= new_j <= self.j_bounds[1]:
                    self.cursor_i, self.cursor_j = new_i, new_j
            elif key == ord('[') or key == ord(',') or key == ord('<'):  # Decrease k layer
                self.current_k = max(self.k_bounds[0], self.current_k - 1)
            elif key == ord(']') or key == ord('.') or key == ord('>'):  # Increase k layer
                self.current_k = min(self.k_bounds[1], self.current_k + 1)
            elif key == ord('a'):  # Select all
                for i in range(self.i_bounds[0], self.i_bounds[1] + 1):
                    for j in range(self.j_bounds[0], self.j_bounds[1] + 1):
                        for k in range(self.k_bounds[0], self.k_bounds[1] + 1):
                            self.selected.add((i, j, k))
            elif key == ord('c') and self.lattice_type != 2:  # Clear all (not hex, 'c' is used for diagonal)
                self.selected.clear()
            elif key == ord('r'):  # Reset/clear all (works for both rectangular and hex)
                self.selected.clear()

    def _draw_interface(self, stdscr):
        """Draw the lattice and interface."""
        height, width = stdscr.getmaxyx()

        # Title
        title = f"VISUAL LATTICE SELECTOR - {'Rectangular' if self.lattice_type == 1 else 'Hexagonal'} Lattice"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)

        # Instructions (different for hex vs rectangular)
        if self.lattice_type == 2:  # Hexagonal
            instructions = [
                "Arrow Keys: Move (6-dir hex)  |  W/E/Z/X: Diagonals  |  Space/Enter: Toggle",
                "[/] or ,/. : K-layer  |  a: Select all  |  r: Clear  |  d: Done  |  q/ESC: Cancel"
            ]
        else:  # Rectangular
            instructions = [
                "Arrow Keys: Move cursor  |  Space/Enter: Toggle  |  [/] or ,/. : K-layer",
                "a: Select all  |  c: Clear all  |  d: Done  |  q/ESC: Cancel"
            ]
        for i, instr in enumerate(instructions):
            stdscr.addstr(2 + i, 2, instr)

        # Current layer and selection count
        info = f"K-Layer: {self.current_k}  |  Selected: {len(self.selected)} cells"
        stdscr.addstr(5, 2, info, curses.A_REVERSE)

        # Draw the lattice
        start_row = 7
        start_col = 4

        if self.lattice_type == 1:  # Rectangular
            self._draw_rectangular_lattice(stdscr, start_row, start_col)
        else:  # Hexagonal (LAT=2)
            self._draw_hexagonal_lattice(stdscr, start_row, start_col)

    def _draw_rectangular_lattice(self, stdscr, start_row, start_col):
        """Draw a rectangular lattice grid."""
        try:
            # Draw column headers (i indices)
            header = "    " + "".join(f"{i:4d}" for i in range(self.i_bounds[0], self.i_bounds[1] + 1))
            stdscr.addstr(start_row, start_col, header)

            # Draw top border
            width = (self.i_bounds[1] - self.i_bounds[0] + 1) * 4 + 1
            stdscr.addstr(start_row + 1, start_col + 4, "┌" + "─" * (width - 2) + "┐")

            # Draw each row
            for j in range(self.j_bounds[0], self.j_bounds[1] + 1):
                row_idx = start_row + 2 + (j - self.j_bounds[0])
                # Row header (j index)
                stdscr.addstr(row_idx, start_col, f"{j:3d} ")

                # Draw cells
                for i in range(self.i_bounds[0], self.i_bounds[1] + 1):
                    col_idx = start_col + 4 + (i - self.i_bounds[0]) * 4

                    cell = (i, j, self.current_k)
                    is_cursor = (i == self.cursor_i and j == self.cursor_j)
                    is_selected = cell in self.selected

                    # Determine what to display
                    if is_selected and is_cursor:
                        char = "█"
                        attr = curses.A_REVERSE | curses.A_BOLD
                    elif is_selected:
                        char = "█"
                        attr = curses.A_BOLD
                    elif is_cursor:
                        char = "░"
                        attr = curses.A_REVERSE
                    else:
                        char = "·"
                        attr = curses.A_NORMAL

                    stdscr.addstr(row_idx, col_idx + 1, f" {char} ", attr)

            # Draw bottom border
            bottom_row = start_row + 2 + (self.j_bounds[1] - self.j_bounds[0] + 1)
            stdscr.addstr(bottom_row, start_col + 4, "└" + "─" * (width - 2) + "┘")

        except curses.error:
            # Screen too small
            stdscr.clear()
            stdscr.addstr(0, 0, "ERROR: Terminal window too small! Please resize and restart.", curses.A_REVERSE)

    def _draw_hexagonal_lattice_compact(self, stdscr, start_row, start_col):
        """
        Draw a compact hexagonal lattice representation.
        Uses single characters with offset rows to show hex pattern.

        Format:
           0   1   2   3   4
         0  ·   ·   X   ·   ·
           1  ·   X   X   X   ·
         2  X   X   ·   X   X
        """
        try:
            i_min, i_max = self.i_bounds
            j_min, j_max = self.j_bounds

            # Draw column header (i indices)
            # Start with 3 spaces for j-label, then center each i-index in 4-char columns
            header = "   "  # Space for j-label
            for i in range(i_min, i_max + 1):
                header += f" {i:2} "  # Center index in 4-char column
            stdscr.addstr(start_row, start_col, header, curses.A_DIM)
            start_row += 1

            # Draw rows
            for j in range(j_min, j_max + 1):
                # Build the row string
                row_str = f"{j:2} "  # j-label (2 chars + space = 3 total)

                # Add offset for odd rows (shift right by 2 spaces to show hex pattern)
                if j % 2 == 1:
                    row_str += "  "  # Offset odd rows

                # Draw cells
                for i in range(i_min, i_max + 1):
                    at_cursor = (i == self.cursor_i and j == self.cursor_j)
                    is_selected = (i, j, self.current_k) in self.selected

                    # Choose character
                    if at_cursor and is_selected:
                        char = "@"  # Cursor + selected
                    elif at_cursor:
                        char = "█"  # Cursor
                    elif is_selected:
                        char = "X"  # Selected
                    else:
                        char = "·"  # Unselected

                    # Add to row (1 space + char + 2 spaces = 4 chars per cell)
                    row_str += f" {char}  "

                # Draw the complete row
                try:
                    # Draw non-highlighted parts
                    col = start_col
                    # Draw j-label
                    stdscr.addstr(start_row, col, f"{j:2} ", curses.A_DIM)
                    col += 3

                    # Add offset for odd rows
                    if j % 2 == 1:
                        col += 2

                    # Draw each cell with appropriate style
                    for i in range(i_min, i_max + 1):
                        at_cursor = (i == self.cursor_i and j == self.cursor_j)
                        is_selected = (i, j, self.current_k) in self.selected

                        if at_cursor and is_selected:
                            char = "@"
                            style = curses.A_REVERSE | curses.A_BOLD
                        elif at_cursor:
                            char = "█"
                            style = curses.A_REVERSE
                        elif is_selected:
                            char = "X"
                            style = curses.A_BOLD
                        else:
                            char = "·"
                            style = curses.A_NORMAL

                        stdscr.addstr(start_row, col, f" {char}  ", style)
                        col += 4

                except curses.error:
                    pass

                start_row += 1

            # Legend
            legend_row = start_row + 2
            stdscr.addstr(legend_row, start_col, "Legend: X=Selected  ·=Unselected  █=Cursor  @=Cursor+Selected", curses.A_DIM)
            stdscr.addstr(legend_row + 1, start_col, "Note: Odd rows (j) shifted right to show hexagonal adjacency", curses.A_DIM)

        except curses.error:
            stdscr.clear()
            stdscr.addstr(0, 0, "ERROR: Terminal window too small! Please resize and restart.", curses.A_REVERSE)

    def _draw_hexagonal_lattice(self, stdscr, start_row, start_col):
        """
        Draw a hexagonal lattice using compact format.
        Uses single-character cells with offset rows to show hex adjacency pattern.
        """
        # Always use compact format for hexagonal lattices
        self._draw_hexagonal_lattice_compact(stdscr, start_row, start_col)

    def _is_selection_contiguous(self) -> bool:
        """
        Check if selected cells form a contiguous rectangular range.

        Returns True if the bounding box exactly matches the selected cells.
        Returns False if there are gaps (non-contiguous selection).
        """
        if not self.selected:
            return True  # Empty is trivially contiguous

        if len(self.selected) == 1:
            return True  # Single element is contiguous

        # Calculate bounding box
        selected_list = list(self.selected)
        i_vals = [cell[0] for cell in selected_list]
        j_vals = [cell[1] for cell in selected_list]
        k_vals = [cell[2] for cell in selected_list]

        i_min, i_max = min(i_vals), max(i_vals)
        j_min, j_max = min(j_vals), max(j_vals)
        k_min, k_max = min(k_vals), max(k_vals)

        # Calculate expected size of bounding box
        expected_count = (i_max - i_min + 1) * (j_max - j_min + 1) * (k_max - k_min + 1)
        actual_count = len(self.selected)

        # Check if all cells in bounding box are selected
        if expected_count == actual_count:
            # Double-check: verify every cell in range is selected
            for i in range(i_min, i_max + 1):
                for j in range(j_min, j_max + 1):
                    for k in range(k_min, k_max + 1):
                        if (i, j, k) not in self.selected:
                            return False
            return True

        return False

    def _create_lattice_spec(self) -> LatticeSpec:
        """
        Create a LatticeSpec from selected cells with auto-detection.

        - If selection is contiguous: creates range-based spec
        - If selection is non-contiguous: creates element-list spec
        """
        if not self.selected:
            return None

        # Check if selection is contiguous
        is_contiguous = self._is_selection_contiguous()

        if is_contiguous:
            # CONTIGUOUS: Use range-based spec (original behavior)
            selected_list = list(self.selected)
            i_vals = [cell[0] for cell in selected_list]
            j_vals = [cell[1] for cell in selected_list]
            k_vals = [cell[2] for cell in selected_list]

            i_min, i_max = min(i_vals), max(i_vals)
            j_min, j_max = min(j_vals), max(j_vals)
            k_min, k_max = min(k_vals), max(k_vals)

            # Create spec (use range if multiple values, otherwise single)
            def make_spec_dim(min_val, max_val):
                if min_val == max_val:
                    return min_val
                else:
                    return (min_val, max_val)

            return LatticeSpec(
                i=make_spec_dim(i_min, i_max),
                j=make_spec_dim(j_min, j_max),
                k=make_spec_dim(k_min, k_max)
            )
        else:
            # NON-CONTIGUOUS: Use element-list spec
            # Sort elements for consistent output
            elements_list = sorted(list(self.selected))

            return LatticeSpec(
                elements=elements_list
            )


def main():
    """Main entry point."""
    wizard = MCNPWizard()
    try:
        wizard.run()
    except KeyboardInterrupt:
        print("\n\nWizard cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Thank you for using the MCNP Universe & Lattice Wizard!")
    print("=" * 70)


if __name__ == "__main__":
    main()
