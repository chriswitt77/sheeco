"""
Plotting utilities for visualizing segments before assembly.
Useful for debugging segment generation and understanding geometry.
"""

import numpy as np
import pyvista as pv


def plot_segments(segments, title="Segment Visualization", separate_windows=False, show_labels=True):
    """
    Plot segments individually or together for visualization and debugging.

    Args:
        segments: List of segment objects (each segment has .tabs dictionary)
        title: Window title for the plot
        separate_windows: If True, plot each segment in a separate window
        show_labels: If True, show point labels
    """
    if not segments:
        print("No segments to plot")
        return

    if separate_windows:
        # Plot each segment in its own window
        for seg_idx, segment in enumerate(segments):
            plotter = pv.Plotter()
            plotter.add_title(f"{title} - Segment {seg_idx + 1}/{len(segments)}")
            _plot_single_segment(plotter, segment, seg_idx, show_labels=show_labels)
            plotter.show()
    else:
        # Plot all segments in one window with spacing
        plotter = pv.Plotter()
        plotter.add_title(f"{title} - All {len(segments)} segments")

        # Calculate spacing to separate segments visually
        spacing = 150  # mm between segments

        for seg_idx, segment in enumerate(segments):
            offset = np.array([seg_idx * spacing, 0, 0])
            _plot_single_segment(plotter, segment, seg_idx, offset=offset, show_labels=show_labels)

        plotter.show()


def _plot_single_segment(plotter, segment, seg_idx, offset=None, show_labels=True):
    """
    Plot a single segment into the given plotter.

    Args:
        plotter: PyVista plotter object
        segment: Segment object with .tabs dictionary
        seg_idx: Index of the segment (for coloring)
        offset: [x, y, z] offset to apply to all points
        show_labels: If True, show point labels
    """
    if offset is None:
        offset = np.array([0, 0, 0])

    # Color scheme
    colors = {
        'tab': ['#648fff', '#dc267f', '#ffb000', '#26dc83', '#785ef0'],
        'corner': '#ff0000',
        'bend': '#00ff00',
        'flange': '#0000ff',
    }

    # Get tabs from segment
    tabs = segment.tabs

    # Plot each tab
    for tab_local_idx, (tab_local_id, tab) in enumerate(tabs.items()):
        # Get all points
        if not tab.points:
            continue

        points_list = list(tab.points.values())
        points_array = np.array(points_list) + offset
        num_points = points_array.shape[0]

        # Create mesh for the tab
        faces = np.hstack([[num_points], np.arange(num_points)])
        mesh = pv.PolyData(points_array, faces=faces)

        # Triangulate if needed (more than 4 points)
        if num_points > 4:
            mesh = mesh.triangulate()

        # Choose color based on tab index
        tab_color = colors['tab'][tab_local_idx % len(colors['tab'])]

        # Plot tab surface
        plotter.add_mesh(
            mesh,
            color=tab_color,
            opacity=0.7,
            show_edges=True,
            label=f"Seg{seg_idx}_Tab{tab_local_id}"
        )

        # Plot points with different colors based on type
        point_ids = list(tab.points.keys())

        for point_id, point_coord in tab.points.items():
            point_3d = point_coord + offset

            # Determine point type and color
            if point_id in ['A', 'B', 'C', 'D']:
                point_color = colors['corner']
                point_size = 15
            elif 'BP' in point_id:
                point_color = colors['bend']
                point_size = 12
            elif 'FP' in point_id:
                point_color = colors['flange']
                point_size = 10
            else:
                point_color = '#808080'  # Gray for unknown
                point_size = 8

            # Plot point
            plotter.add_points(
                point_3d,
                color=point_color,
                point_size=point_size,
                render_points_as_spheres=True
            )

            # Add label if requested
            if show_labels:
                label_text = f"{point_id}"
                plotter.add_point_labels(
                    point_3d,
                    [label_text],
                    font_size=10,
                    text_color='black',
                    show_points=False,
                    always_visible=False
                )

    # Add legend
    legend_text = f"""
Segment {seg_idx + 1}:
  {len(tabs)} tabs

Point types:
  Red = Corners (A,B,C,D)
  Green = Bend Points (BP)
  Blue = Flange Points (FP)
"""
    plotter.add_text(legend_text, position="lower_left", font_size=12)


def plot_segment_pair(segment, pair_ids=None, title="Segment Pair Visualization"):
    """
    Plot a segment that connects two tabs, with clear visualization of the connection.

    Args:
        segment: Segment object
        pair_ids: Tuple of (tab_x_id, tab_z_id) for labeling
        title: Window title
    """
    plotter = pv.Plotter()

    if pair_ids:
        plotter.add_title(f"{title} - Pair {pair_ids}")
    else:
        plotter.add_title(title)

    _plot_single_segment(plotter, segment, 0, show_labels=True)

    # Add arrows showing connection direction if it's a two-tab segment
    tabs_list = list(segment.tabs.values())
    if len(tabs_list) >= 2:
        # Get centers of first and last tab
        points_0 = np.array(list(tabs_list[0].points.values()))
        points_n = np.array(list(tabs_list[-1].points.values()))

        center_0 = points_0.mean(axis=0)
        center_n = points_n.mean(axis=0)

        # Draw arrow from first to last
        arrow = pv.Arrow(start=center_0, direction=center_n - center_0, scale='auto')
        plotter.add_mesh(arrow, color='red', opacity=0.5)

    plotter.show()


def plot_segments_for_sequence(part, sequence, segment_cfg, filter_cfg, max_per_pair=3):
    """
    Generate and plot segments for each pair in a sequence.

    Args:
        part: Initialized Part object
        sequence: List of [tab_x_id, tab_z_id] pairs
        segment_cfg: Configuration for segment generation
        filter_cfg: Configuration for filtering
        max_per_pair: Maximum number of segments to plot per pair
    """
    from src.hgen_sm import Part as PartClass, create_segments

    for pair_idx, pair in enumerate(sequence):
        print(f"\nPair {pair_idx + 1}/{len(sequence)}: {pair}")

        tab_x = part.tabs[pair[0]]
        tab_z = part.tabs[pair[1]]

        segment_tabs = {'tab_x': tab_x, 'tab_z': tab_z}
        segment_part = PartClass(sequence=pair, tabs=segment_tabs)
        segments = create_segments(segment_part, segment_cfg, filter_cfg)

        print(f"  Generated {len(segments)} segments")

        if len(segments) == 0:
            print(f"  [WARNING] No segments generated for this pair!")
            continue

        # Plot up to max_per_pair segments
        segments_to_plot = segments[:max_per_pair]
        if len(segments) > max_per_pair:
            print(f"  Plotting first {max_per_pair} of {len(segments)} segments")

        plot_segments(
            segments_to_plot,
            title=f"Pair {pair} - Segments",
            separate_windows=False,
            show_labels=True
        )


def plot_segments_with_edge_colors(segments, title="Segments with Edge Highlighting"):
    """
    Plot segments with edge highlighting to show which edges are being used.

    Args:
        segments: List of segment objects
        title: Window title
    """
    plotter = pv.Plotter()
    plotter.add_title(title)

    spacing = 150
    for seg_idx, segment in enumerate(segments):
        offset = np.array([seg_idx * spacing, 0, 0])

        # Plot the segment normally
        _plot_single_segment(plotter, segment, seg_idx, offset=offset, show_labels=True)

        # Highlight edges being used
        for tab_local_id, tab in segment.tabs.items():
            if not tab.points:
                continue

            # Find corner points
            corners = {}
            for corner in ['A', 'B', 'C', 'D']:
                if corner in tab.points:
                    corners[corner] = tab.points[corner] + offset

            if len(corners) < 4:
                continue

            # Check which edges have non-corner points nearby
            edges = [
                ('AB', corners['A'], corners['B']),
                ('BC', corners['B'], corners['C']),
                ('CD', corners['C'], corners['D']),
                ('DA', corners['D'], corners['A']),
            ]

            # Get non-corner points
            non_corner_points = [(name, coord + offset) for name, coord in tab.points.items()
                                if name not in ['A', 'B', 'C', 'D']]

            # Highlight edges with points
            for edge_name, p1, p2 in edges:
                has_points = False

                for point_name, point_coord in non_corner_points:
                    # Check if point is near this edge
                    vec_edge = p2 - p1
                    vec_to_point = point_coord - p1

                    if np.linalg.norm(vec_edge) > 1e-6:
                        t = np.dot(vec_to_point, vec_edge) / np.dot(vec_edge, vec_edge)

                        if -0.1 <= t <= 1.1:
                            projected = p1 + t * vec_edge
                            dist = np.linalg.norm(point_coord - projected)

                            if dist < 15.0:
                                has_points = True
                                break

                # Draw edge line
                if has_points:
                    line = pv.Line(p1, p2)
                    plotter.add_mesh(line, color='red', line_width=5, label=f"{edge_name}_used")

    plotter.show()
