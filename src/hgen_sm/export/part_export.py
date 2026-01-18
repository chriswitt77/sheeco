import os
import json
import datetime
import math

def create_timestamp():
    now = datetime.datetime.now()
    timestamp = now.strftime("%y%m%d_%H%M")

    return timestamp

def create_part_json(part, timestamp = None):
    if timestamp is None:
        timestamp = create_timestamp()

    # 2. Prepare Data (Convert NumPy arrays to lists)
    export_data = {
        "timestamp": timestamp,
        "part_id": part.part_id,
        "tabs": {}
    }

    for tid, tab in part.tabs.items():
        # Export tab points
        tab_data = {
            "points": {label: pt.tolist() for label, pt in tab.points.items()}
        }

        # Export mounts/holes if present
        if hasattr(tab, 'mounts') and tab.mounts:
            tab_data["mounts"] = []
            for mount in tab.mounts:
                mount_data = {
                    "u": float(mount.u),
                    "v": float(mount.v),
                    "size": float(mount.size),
                    "type": mount.type
                }
                # Include global coordinates if available
                if mount.global_coords is not None:
                    mount_data["global_coords"] = mount.global_coords.tolist()
                tab_data["mounts"].append(mount_data)

        export_data["tabs"][tid] = tab_data

    return export_data

def export_to_json(part, output_dir="exports"):
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Assuming part.tabs is a dict of your tab objects
    num_tabs = len(part.tabs)
    num_rects = getattr(part, 'number_rectangles', num_tabs) 
    
    timestamp = create_timestamp()

    filename = f"{timestamp}_part{part.part_id}_{num_rects}rects_{num_tabs}tabs.json"
    filepath = os.path.join(output_dir, filename)

    export_data = create_part_json(part, timestamp)    

    # 3. Write to file
    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=4)

    print(f"Exported solution to: {filepath}")
    return filepath

# WARNING: THIS SECTION IS STILL EXPERIMENTAL
def export_to_onshape(part, output_dir="exports"):
    part_json = create_part_json(part)
    # Vector helpers
    sub = lambda a, b: [a[i] - b[i] for i in range(3)]
    cross = lambda a, b: [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
    dot = lambda a, b: sum(x*y for x, y in zip(a, b))
    norm = lambda v: [x / m for x in v] if (m := math.sqrt(sum(x*x for x in v))) else v
    mag_sq = lambda v: sum(x*x for x in v)

    fs = [
        'FeatureScript 2837;',
        'import(path : "onshape/std/geometry.fs", version : "2837.0");',
        'annotation { "Feature Type Name" : "hgen-sm-part" }',
        'export const jsonImport = defineFeature(function(context is Context, id is Id, definition is map)',
        '    precondition { }',
        '    {',
        '        const thickness = 1.0 * millimeter;'
    ]
    extrude_queries = []

    for tab_id, tab_data in part_json.get("tabs", {}).items():
        pts = list(tab_data["points"].values())
        if len(pts) < 3: continue

        # --- Plane Detection & Basis Calculation ---
        # For tabs with A, B, C corners, use them for coordinate system
        # For intermediate tabs (from two-bend), use first three non-collinear points
        points_dict = tab_data["points"]

        # Try to use A, B, C if available (original rectangles)
        if 'A' in points_dict and 'B' in points_dict and 'C' in points_dict:
            A = points_dict['A']
            B = points_dict['B']
            C = points_dict['C']
            origin = A
            v1 = sub(B, A)
            v2 = sub(C, A)
        else:
            # Intermediate tab - use first three points to establish coordinate system
            origin = pts[0]
            v1 = sub(pts[1], pts[0])
            # Find a non-collinear third point
            v2 = None
            for i in range(2, len(pts)):
                v_temp = sub(pts[i], pts[0])
                cp = cross(v1, v_temp)
                if mag_sq(cp) > 1e-8:
                    v2 = v_temp
                    break

            if v2 is None:
                print(f"Skipping Tab {tab_id}: All points are collinear.")
                continue

        # Calculate plane normal and coordinate axes
        z_axis = cross(v1, v2)
        if mag_sq(z_axis) < 1e-8:
            print(f"Skipping Tab {tab_id}: Points are collinear.")
            continue

        z_axis = norm(z_axis)
        x_axis = norm(v1)  # x-axis along first edge direction
        y_axis = cross(z_axis, x_axis)  # y-axis perpendicular in plane

        # Filter points for export:
        # 1. Skip FP points ONLY if they're duplicates (at corner coordinates)
        #    For intermediate tabs, FP points define flange geometry and must be kept
        # 2. Remove other consecutive duplicates
        point_ids = list(tab_data["points"].keys())
        filtered_pts = []
        filtered_ids = []
        tolerance = 1e-6

        for i, (point_id, p) in enumerate(zip(point_ids, pts)):
            # Check if this point is a duplicate of any already-added point
            is_duplicate = False
            for existing_pt in filtered_pts:
                dist = math.sqrt(sum((p[j] - existing_pt[j])**2 for j in range(3)))
                if dist < tolerance:
                    is_duplicate = True
                    break

            # Skip duplicates (this catches FP points at corner coordinates)
            if is_duplicate:
                continue

            # Add unique points
            filtered_pts.append(p)
            filtered_ids.append(point_id)

        # Project 3D points to 2D local plane (relative to origin)
        points_2d = []
        for p in filtered_pts:
            vec = sub(p, origin)  # Use calculated origin
            u, v = dot(vec, x_axis), dot(vec, y_axis)
            points_2d.append(f"vector({u}, {v}) * millimeter")

        # Ensure the loop is closed for 2D sketch
        # Check if first and last are different before closing
        if len(points_2d) > 0:
            first_pt = filtered_pts[0]
            last_pt = filtered_pts[-1]
            dist = math.sqrt(sum((first_pt[j] - last_pt[j])**2 for j in range(3)))
            if dist > tolerance:
                points_2d.append(points_2d[0])

        # Format Vectors for FS (use calculated origin as sketch plane origin)
        fs_org = f"vector({origin[0]}, {origin[1]}, {origin[2]}) * millimeter"
        fs_norm = f"vector({z_axis[0]}, {z_axis[1]}, {z_axis[2]})"
        fs_x = f"vector({x_axis[0]}, {x_axis[1]}, {x_axis[2]})"

        # --- Generate FeatureScript ---
        fs.append(f'')
        fs.append(f'        // --- Tab {tab_id} ---')
        fs.append(f'        var sketch{tab_id} = newSketchOnPlane(context, id + "sketch{tab_id}", {{ "sketchPlane" : plane({fs_org}, {fs_norm}, {fs_x}) }});')
        fs.append(f'        skPolyline(sketch{tab_id}, "poly{tab_id}", {{ "points" : [{", ".join(points_2d)}] }});')
        fs.append(f'        skSolve(sketch{tab_id});')

        # Extrude the tab body first (without holes)
        fs.append(f'        opExtrude(context, id + "extrude{tab_id}", {{')
        fs.append(f'            "entities" : qSketchRegion(id + "sketch{tab_id}"),')
        fs.append(f'            "direction" : {fs_norm},')
        fs.append(f'            "endBound" : BoundingType.BLIND,')
        fs.append(f'            "endDepth" : thickness')
        fs.append(f'        }});')

        # --- Create mount holes as boolean cuts ---
        if "mounts" in tab_data:
            for mount_idx, mount in enumerate(tab_data["mounts"]):
                # Mount coordinates are in local (u, v) system
                mount_u = mount["u"]
                mount_v = mount["v"]
                mount_radius = mount["size"]

                # Convert mount center from 2D local to 3D global coordinates
                mount_center_3d = [
                    origin[0] + mount_u * x_axis[0] + mount_v * y_axis[0],
                    origin[1] + mount_u * x_axis[1] + mount_v * y_axis[1],
                    origin[2] + mount_u * x_axis[2] + mount_v * y_axis[2]
                ]

                fs.append(f'')
                fs.append(f'        // Mount hole {mount_idx} for tab {tab_id}')
                fs.append(f'        var sketchHole{tab_id}_{mount_idx} = newSketchOnPlane(context, id + "sketchHole{tab_id}_{mount_idx}", {{')
                fs.append(f'            "sketchPlane" : plane(vector({mount_center_3d[0]}, {mount_center_3d[1]}, {mount_center_3d[2]}) * millimeter, {fs_norm}, {fs_x})')
                fs.append(f'        }});')
                fs.append(f'        skCircle(sketchHole{tab_id}_{mount_idx}, "holeCircle{tab_id}_{mount_idx}", {{')
                fs.append(f'            "center" : vector(0, 0) * millimeter,')
                fs.append(f'            "radius" : {mount_radius} * millimeter')
                fs.append(f'        }});')
                fs.append(f'        skSolve(sketchHole{tab_id}_{mount_idx});')
                fs.append(f'        opExtrude(context, id + "extrudeHole{tab_id}_{mount_idx}", {{')
                fs.append(f'            "entities" : qSketchRegion(id + "sketchHole{tab_id}_{mount_idx}"),')
                fs.append(f'            "direction" : {fs_norm},')
                fs.append(f'            "endBound" : BoundingType.BLIND,')
                fs.append(f'            "endDepth" : thickness * 2')  # Make it longer to ensure it cuts through
                fs.append(f'        }});')
                fs.append(f'        opBoolean(context, id + "cutHole{tab_id}_{mount_idx}", {{')
                fs.append(f'            "targets" : qCreatedBy(id + "extrude{tab_id}", EntityType.BODY),')
                fs.append(f'            "tools" : qCreatedBy(id + "extrudeHole{tab_id}_{mount_idx}", EntityType.BODY),')
                fs.append(f'            "operationType" : BooleanOperationType.SUBTRACTION')
                fs.append(f'        }});')
        extrude_queries.append(f'qCreatedBy(id + "extrude{tab_id}", EntityType.BODY)')

    # --- Merge Operation ---
    if extrude_queries:
        fs.append(f'')
        fs.append(f'        opBoolean(context, id + "unionBodies", {{')
        fs.append(f'            "tools" : qUnion([{", ".join(extrude_queries)}]),')
        fs.append(f'            "operationType" : BooleanOperationType.UNION')
        fs.append(f'        }});')

    fs.append('    });')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = create_timestamp()
    num_rects = len(part.tabs)
    num_tabs = len(part.tabs)

    filename = f"{timestamp}_part{part.part_id}_{num_rects}rects_{num_tabs}tabs.fs"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w') as f:
        f.write("\n".join(fs))
    print(f"Done. Copy {filepath} to Onshape.")