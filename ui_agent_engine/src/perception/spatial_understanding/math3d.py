import math
import numpy as np
from typing import List, Tuple, Dict, Any

def euler_to_quaternion(rpy: List[float]) -> List[float]:
    """Convert Euler angles (roll, pitch, yaw) in radians to quaternion."""
    sr = math.sin(rpy[0] / 2.0)
    sp = math.sin(rpy[1] / 2.0)
    sy = math.sin(rpy[2] / 2.0)
    
    cr = math.cos(rpy[0] / 2.0)
    cp = math.cos(rpy[1] / 2.0)
    cz = math.cos(rpy[2] / 2.0)
    
    return [
        sr * cp * cz - cr * sp * sy,
        cr * sp * cz + sr * cp * sy,
        cr * cp * sy - sr * sp * cz,
        cr * cp * cz + sr * sp * sy,
    ]

def quaternion_to_rotation_matrix(q: List[float]) -> np.ndarray:
    """Create a 3x3 rotation matrix from a quaternion [x, y, z, w]."""
    q0, q1, q2, q3 = q
    
    return np.array([
        [
            1 - 2 * q1**2 - 2 * q2**2,
            2 * q0 * q1 - 2 * q3 * q2,
            2 * q0 * q2 + 2 * q3 * q1,
        ],
        [
            2 * q0 * q1 + 2 * q3 * q2,
            1 - 2 * q0**2 - 2 * q2**2,
            2 * q1 * q2 - 2 * q3 * q0,
        ],
        [
            2 * q0 * q2 - 2 * q3 * q1,
            2 * q1 * q2 + 2 * q3 * q0,
            1 - 2 * q0**2 - 2 * q1**2,
        ],
    ])

def generate_box_corners(size: List[float]) -> np.ndarray:
    """Generate 8 corners of a 3D bounding box in local coordinates."""
    hx, hy, hz = [s / 2.0 for s in size]
    
    corners = []
    for x in [-hx, hx]:
        for y in [-hy, hy]:
            for z in [-hz, hz]:
                corners.append((x, y, z))
                
    # Reorder corners to match exact client-side JS implementation
    ordered = [
        corners[1],  # +x, -y, -z
        corners[3],  # +x, +y, -z
        corners[7],  # +x, +y, +z
        corners[5],  # +x, -y, +z
        corners[0],  # -x, -y, -z
        corners[2],  # -x, +y, -z
        corners[6],  # -x, +y, +z
        corners[4],  # -x, -y, +z
    ]
    return np.array(ordered)

def calculate_camera_intrinsics(width: float, height: float, fov: float) -> np.ndarray:
    """Calculate 3x3 camera intrinsic matrix."""
    f = width / (2.0 * math.tan(math.radians(fov / 2.0)))
    cx = width / 2.0
    cy = height / 2.0
    
    return np.array([
        [f, 0, cx],
        [0, f, cy],
        [0, 0, 1],
    ])

def create_view_rotation_matrix() -> np.ndarray:
    """Create view rotation matrix (90-degree tilt)."""
    tilt_angle = 90.0
    radians = math.radians(tilt_angle)
    
    return np.array([
        [1, 0, 0],
        [0, math.cos(radians), -math.sin(radians)],
        [0, math.sin(radians), math.cos(radians)],
    ])

def project_3d_bounding_box(box: Dict[str, Any], width: float, height: float, fov: float) -> Dict[str, Any]:
    """Project 3D bounding box to 2D screen coordinates."""
    center = np.array(box['center'])
    size = box['size']
    rpy = box['rpy']
    label = box['label']
    
    quaternion = euler_to_quaternion(rpy)
    intrinsics = calculate_camera_intrinsics(width, height, fov)
    corners = generate_box_corners(size)
    rotation_matrix = quaternion_to_rotation_matrix(quaternion)
    
    # Rotate corners locally and translate to world center
    box_vertices = np.array([np.dot(rotation_matrix, c) + center for c in corners])
    
    view_rotation_matrix = create_view_rotation_matrix()
    
    # Apply global view rotation
    rotated_points = np.array([np.dot(view_rotation_matrix, p) for p in box_vertices])
    
    # Project to 2D
    projected_points = np.array([np.dot(intrinsics, p) for p in rotated_points])
    
    vertices_2d = [(p[0] / p[2], p[1] / p[2]) if p[2] != 0 else (0,0) for p in projected_points]
    
    top_vertices = vertices_2d[0:4]
    bottom_vertices = vertices_2d[4:8]
    
    lines = []
    
    for i in range(4):
        wireframe_lines = [
            (top_vertices[i], top_vertices[(i + 1) % 4]), # Top face edges
            (bottom_vertices[i], bottom_vertices[(i + 1) % 4]), # Bottom face edges
            (top_vertices[i], bottom_vertices[i]), # Vertical edges
        ]
        
        for start, end in wireframe_lines:
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)
            lines.append({"start": start, "end": end, "length": length, "angle": angle})

    # Label position logic
    text_position_3d = np.mean(box_vertices, axis=0)
    text_position_3d[2] += 0.1 # Slight offset in Z
    
    text_point = np.dot(intrinsics, np.dot(view_rotation_matrix, text_position_3d))
    label_pos = (text_point[0] / text_point[2], text_point[1] / text_point[2]) if text_point[2] != 0 else (0,0)

    return {
        "lines": lines,
        "label": {
            "label": label,
            "pos": label_pos,
            "center": center.tolist()
        }
    }

def project_all_3d_bounding_boxes(boxes: List[Dict[str, Any]], width: float, height: float, fov: float) -> Dict[str, Any]:
    """Project multiple 3D bounding boxes."""
    all_lines = []
    all_labels = []
    for box in boxes:
        projection = project_3d_bounding_box(box, width, height, fov)
        all_lines.extend(projection["lines"])
        all_labels.append(projection["label"])
        
    return {"lines": all_lines, "labels": all_labels}
