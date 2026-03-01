/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * 3D Mathematics Module
 * Contains all 3D bounding box calculations, projections, and transformations
 * Matches the client-side implementation exactly
 */

/**
 * Matrix multiplication helper
 * @param {Array<Array<number>>} matrix - Matrix to multiply
 * @param {Array<number>} vector - Vector to multiply
 * @returns {Array<number>} Result vector
 */
export function matrixMultiply(matrix, vector) {
  return matrix.map(row => 
    row.reduce((sum, val, i) => sum + val * vector[i], 0)
  );
}

/**
 * Convert Euler angles to quaternion
 * @param {Array<number>} rpy - Roll, pitch, yaw in radians
 * @returns {Array<number>} Quaternion [x, y, z, w]
 */
export function eulerToQuaternion(rpy) {
  const [sr, sp, sy] = rpy.map(x => Math.sin(x / 2));
  const [cr, cp, cz] = rpy.map(x => Math.cos(x / 2));
  
  return [
    sr * cp * cz - cr * sp * sy,
    cr * sp * cz + sr * cp * sy,
    cr * cp * sy - sr * sp * cz,
    cr * cp * cz + sr * sp * sy,
  ];
}

/**
 * Create rotation matrix from quaternion
 * @param {Array<number>} quaternion - Quaternion [x, y, z, w]
 * @returns {Array<Array<number>>} 3x3 rotation matrix
 */
export function quaternionToRotationMatrix(quaternion) {
  const [q0, q1, q2, q3] = quaternion;
  
  return [
    [
      1 - 2 * q1 ** 2 - 2 * q2 ** 2,
      2 * q0 * q1 - 2 * q3 * q2,
      2 * q0 * q2 + 2 * q3 * q1,
    ],
    [
      2 * q0 * q1 + 2 * q3 * q2,
      1 - 2 * q0 ** 2 - 2 * q2 ** 2,
      2 * q1 * q2 - 2 * q3 * q0,
    ],
    [
      2 * q0 * q2 - 2 * q3 * q1,
      2 * q1 * q2 + 2 * q3 * q0,
      1 - 2 * q0 ** 2 - 2 * q1 ** 2,
    ],
  ];
}

/**
 * Generate 8 corners of a 3D bounding box
 * @param {Array<number>} size - [width, height, depth]
 * @returns {Array<Array<number>>} 8 corner points in local coordinates
 */
export function generateBoxCorners(size) {
  const halfSize = size.map(s => s / 2);
  let corners = [];
  
  for (let x of [-halfSize[0], halfSize[0]]) {
    for (let y of [-halfSize[1], halfSize[1]]) {
      for (let z of [-halfSize[2], halfSize[2]]) {
        corners.push([x, y, z]);
      }
    }
  }
  
  // Reorder corners to match client-side ordering
  return [
    corners[1],  // +x, -y, -z
    corners[3],  // +x, +y, -z
    corners[7],  // +x, +y, +z
    corners[5],  // +x, -y, +z
    corners[0],  // -x, -y, -z
    corners[2],  // -x, +y, -z
    corners[6],  // -x, +y, +z
    corners[4],  // -x, -y, +z
  ];
}

/**
 * Calculate camera intrinsic parameters
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @param {number} fov - Field of view in degrees
 * @returns {Array<Array<number>>} 3x3 intrinsic matrix
 */
export function calculateCameraIntrinsics(width, height, fov) {
  const f = width / (2 * Math.tan(((fov / 2) * Math.PI) / 180));
  const cx = width / 2;
  const cy = height / 2;
  
  return [
    [f, 0, cx],
    [0, f, cy],
    [0, 0, 1],
  ];
}

/**
 * Create view rotation matrix (90-degree tilt)
 * @returns {Array<Array<number>>} 3x3 view rotation matrix
 */
export function createViewRotationMatrix() {
  const tiltAngle = 90.0;
  const radians = (tiltAngle * Math.PI) / 180;
  
  return [
    [1, 0, 0],
    [0, Math.cos(radians), -Math.sin(radians)],
    [0, Math.sin(radians), Math.cos(radians)],
  ];
}

/**
 * Project 3D bounding box to 2D screen coordinates
 * @param {Object} box - 3D bounding box {center, size, rpy, label}
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @param {number} fov - Field of view in degrees
 * @returns {Object} Projected lines and label position
 */
export function project3DBoundingBox(box, width, height, fov) {
  const { center, size, rpy, label } = box;
  
  // Convert Euler angles to quaternion
  const quaternion = eulerToQuaternion(rpy);
  
  // Calculate camera parameters
  const intrinsics = calculateCameraIntrinsics(width, height, fov);
  
  // Generate box corners
  const corners = generateBoxCorners(size);
  
  // Apply rotation from quaternion
  const rotationMatrix = quaternionToRotationMatrix(quaternion);
  
  const boxVertices = corners.map(corner => {
    const rotated = matrixMultiply(rotationMatrix, corner);
    return rotated.map((val, idx) => val + center[idx]);
  });
  
  // Apply view rotation
  const viewRotationMatrix = createViewRotationMatrix();
  const rotatedPoints = boxVertices.map(p => 
    matrixMultiply(viewRotationMatrix, p)
  );
  
  // Translate points (no translation in this case)
  const translatedPoints = rotatedPoints.map(p => p.map(v => v + 0));
  
  // Project to 2D
  const projectedPoints = translatedPoints.map(p => 
    matrixMultiply(intrinsics, p)
  );
  
  const vertices = projectedPoints.map(p => [p[0] / p[2], p[1] / p[2]]);
  
  // Generate lines for wireframe
  const topVertices = vertices.slice(0, 4);
  const bottomVertices = vertices.slice(4, 8);
  const lines = [];
  
  for (let i = 0; i < 4; i++) {
    const wireframeLines = [
      [topVertices[i], topVertices[(i + 1) % 4]], // Top face edges
      [bottomVertices[i], bottomVertices[(i + 1) % 4]], // Bottom face edges
      [topVertices[i], bottomVertices[i]], // Vertical edges
    ];
    
    for (let [start, end] of wireframeLines) {
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      const length = Math.sqrt(dx * dx + dy * dy);
      const angle = Math.atan2(dy, dx);
      
      lines.push({ start, end, length, angle });
    }
  }
  
  // Calculate label position (center of all points, slightly offset)
  const textPosition3d = boxVertices[0].map((_, idx) => 
    boxVertices.reduce((sum, p) => sum + p[idx], 0) / boxVertices.length
  );
  textPosition3d[2] += 0.1; // Slight offset in Z
  
  const textPoint = matrixMultiply(
    intrinsics,
    matrixMultiply(viewRotationMatrix, textPosition3d.map(v => v + 0))
  );
  
  const labelPos = [
    textPoint[0] / textPoint[2],
    textPoint[1] / textPoint[2],
  ];
  
  return {
    lines,
    label: { label, pos: labelPos, center }
  };
}

/**
 * Project multiple 3D bounding boxes
 * @param {Array<Object>} boundingBoxes3D - Array of 3D bounding boxes
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @param {number} fov - Field of view in degrees
 * @returns {Object} All projected lines and labels
 */
export function projectAll3DBoundingBoxes(boundingBoxes3D, width, height, fov) {
  const allLines = [];
  const allLabels = [];
  
  for (const box of boundingBoxes3D) {
    const projection = project3DBoundingBox(box, width, height, fov);
    allLines.push(...projection.lines);
    allLabels.push(projection.label);
  }
  
  return { lines: allLines, labels: allLabels };
}

/**
 * Calculate 3D bounding box vertices for coordinate display
 * @param {Object} box - 3D bounding box {center, size, rpy}
 * @returns {Array<Array<number>>} World coordinates of all 8 corners
 */
export function calculate3DBoxVertices(box) {
  const { center, size, rpy } = box;
  
  // Generate corners in local coordinates
  const corners = generateBoxCorners(size);
  
  // Convert Euler angles to quaternion and then to rotation matrix
  const quaternion = eulerToQuaternion(rpy);
  const rotationMatrix = quaternionToRotationMatrix(quaternion);
  
  // Apply rotation and translation to get world coordinates
  return corners.map(corner => {
    const rotated = matrixMultiply(rotationMatrix, corner);
    return rotated.map((val, idx) => val + center[idx]);
  });
}

/**
 * Validate 3D bounding box data
 * @param {Object} box - 3D bounding box to validate
 * @returns {boolean} True if valid
 */
export function validate3DBoundingBox(box) {
  if (!box || typeof box !== 'object') return false;
  
  const { center, size, rpy, label } = box;
  
  // Validate center (3D point)
  if (!Array.isArray(center) || center.length !== 3) return false;
  if (!center.every(c => typeof c === 'number' && !isNaN(c))) return false;
  
  // Validate size (3D dimensions)
  if (!Array.isArray(size) || size.length !== 3) return false;
  if (!size.every(s => typeof s === 'number' && !isNaN(s) && s > 0)) return false;
  
  // Validate rotation (roll, pitch, yaw)
  if (!Array.isArray(rpy) || rpy.length !== 3) return false;
  if (!rpy.every(r => typeof r === 'number' && !isNaN(r))) return false;
  
  // Validate label
  if (typeof label !== 'string' || label.length === 0) return false;
  
  return true;
} 