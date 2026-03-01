import numpy as np
import math

def calculate_bezier_curve(start, end, control1, control2, num_points, use_bell_curve=True):
    """
    Calculates points along a cubic Bezier curve.
    If use_bell_curve is True, adjusts t to be slower at start and end.
    """
    if use_bell_curve:
        # Generate non-linear t: 3t^2 - 2t^3 (Smoothstep) for bell-curve velocity
        t_linear = np.linspace(0, 1, num_points)
        t = 3 * t_linear**2 - 2 * t_linear**3
    else:
        t = np.linspace(0, 1, num_points)
    
    # Unpack points
    x0, y0 = start
    x1, y1 = control1
    x2, y2 = control2
    x3, y3 = end
    
    # Bezier curve formula
    x = (1 - t)**3 * x0 + 3 * (1 - t)**2 * t * x1 + 3 * (1 - t) * t**2 * x2 + t**3 * x3
    y = (1 - t)**3 * y0 + 3 * (1 - t)**2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3 * y3
    
    return np.column_stack((x, y))

def generate_human_like_path(start, end, max_deviation=50, num_points=50):
    """
    Generates a human-like path between two points using a Bezier curve with random control points.
    Includes bio-fidelity speed scaling (Slow-Fast-Slow).
    """
    x0, y0 = start
    x3, y3 = end
    
    # Distance between points
    dist = math.hypot(x3 - x0, y3 - y0)
    
    # Scale deviation based on distance
    deviation = min(max_deviation, dist * 0.2)
    
    # Generate random control points
    dx = (x3 - x0) / 3
    dy = (y3 - y0) / 3
    
    # Add randomness to control points for a unique "hand-drawn" curve every time
    cx1 = x0 + dx + np.random.uniform(-deviation, deviation)
    cy1 = y0 + dy + np.random.uniform(-deviation, deviation)
    
    cx2 = x0 + 2*dx + np.random.uniform(-deviation, deviation)
    cy2 = y0 + 2*dy + np.random.uniform(-deviation, deviation)
    
    # Ensure minimum number of points for smooth rendering
    num_points = max(15, int(dist / 8)) 
    
    path = calculate_bezier_curve(start, (x3, y3), (cx1, cy1), (cx2, cy2), num_points)
    
    # Convert path to integer coordinates
    return np.round(path).astype(int)
