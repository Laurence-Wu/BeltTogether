"""
VL53L5CX Time-of-Flight Sensor Realistic Simulator
Based on STMicroelectronics VL53L5CX datasheet (DS13754 - Rev 5)

Key Features Implemented:
1. Correct Field of View: 45° horizontal × 45° vertical (63° diagonal)
2. Lens Flipping: Horizontal and vertical image flip (zone 0 at bottom-left of SPAD sees top-right scene)
3. Realistic Accuracy: ±15 mm (20-200 mm), ±4.5% (201-4000 mm)
4. 4×4 and 8×8 zone support
5. Range limits: 20-4000 mm
6. Multi-Ray Per Zone: Simulates multiple SPADs per zone with configurable sub-ray sampling
   - Each zone can cast 1, 4, 9, 16, or 25 rays (1×1, 2×2, 3×3, 4×4, 5×5)
   - Aggregates closest detection (first-photon return behavior)
   - More realistic SPAD array simulation
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


# ============================================================================
# 3D Objects
# ============================================================================

class Sphere:
    """A sphere object in 3D space"""
    def __init__(self, center, radius):
        self.center = np.array(center)
        self.radius = radius

    def intersect_ray(self, ray_origin, ray_direction):
        """Ray-sphere intersection using quadratic formula"""
        ray_direction = ray_direction / np.linalg.norm(ray_direction)
        oc = ray_origin - self.center

        a = np.dot(ray_direction, ray_direction)
        b = 2.0 * np.dot(oc, ray_direction)
        c = np.dot(oc, oc) - self.radius**2

        discriminant = b**2 - 4*a*c

        if discriminant < 0:
            return None

        t1 = (-b - np.sqrt(discriminant)) / (2.0*a)
        t2 = (-b + np.sqrt(discriminant)) / (2.0*a)

        if t1 > 0:
            return t1
        elif t2 > 0:
            return t2
        else:
            return None


class Plane:
    """A plane object in 3D space"""
    def __init__(self, point, normal):
        self.point = np.array(point)
        self.normal = np.array(normal) / np.linalg.norm(normal)

    def intersect_ray(self, ray_origin, ray_direction):
        """Ray-plane intersection"""
        ray_direction = ray_direction / np.linalg.norm(ray_direction)
        denom = np.dot(self.normal, ray_direction)

        if abs(denom) < 1e-6:
            return None

        t = np.dot(self.point - ray_origin, self.normal) / denom

        if t > 0:
            return t
        else:
            return None


class Cube:
    """A cube object in 3D space"""
    def __init__(self, center, size):
        self.center = np.array(center)
        self.size = size
        self.faces = []

        # Define 6 faces
        self.faces.append(Plane(center + np.array([0, 0, size/2]), np.array([0, 0, 1])))
        self.faces.append(Plane(center + np.array([0, 0, -size/2]), np.array([0, 0, -1])))
        self.faces.append(Plane(center + np.array([size/2, 0, 0]), np.array([1, 0, 0])))
        self.faces.append(Plane(center + np.array([-size/2, 0, 0]), np.array([-1, 0, 0])))
        self.faces.append(Plane(center + np.array([0, size/2, 0]), np.array([0, 1, 0])))
        self.faces.append(Plane(center + np.array([0, -size/2, 0]), np.array([0, -1, 0])))

    def intersect_ray(self, ray_origin, ray_direction):
        """Ray-cube intersection"""
        min_distance = None

        for face in self.faces:
            distance = face.intersect_ray(ray_origin, ray_direction)

            if distance is not None:
                intersection_point = ray_origin + distance * (ray_direction / np.linalg.norm(ray_direction))
                relative_point = intersection_point - self.center

                if (abs(relative_point[0]) <= self.size/2 + 0.01 and
                    abs(relative_point[1]) <= self.size/2 + 0.01 and
                    abs(relative_point[2]) <= self.size/2 + 0.01):

                    if min_distance is None or distance < min_distance:
                        min_distance = distance

        return min_distance


# ============================================================================
# VL53L5CX Realistic Sensor Simulator
# ============================================================================

class VL53L5CXSensor:
    """
    Simulates VL53L5CX Time-of-Flight sensor with realistic characteristics.

    Datasheet specifications:
    - FoV: 45° horizontal, 45° vertical (63° diagonal)
    - Resolution: 4×4 (16 zones) or 8×8 (64 zones)
    - Range: 20-4000 mm (2-400 cm)
    - Accuracy: ±15 mm (20-200 mm), ±4.5% (201-4000 mm)
    - Lens flips image horizontally and vertically
    - Zone 0 at bottom-left of SPAD array sees top-right of scene
    """

    def __init__(self, position, direction, grid_size=4, add_noise=True, unit='mm', rays_per_zone=1):
        """
        Parameters
        ----------
        position : array-like
            3D position of sensor (origin)
        direction : array-like
            Direction sensor points (will be normalized)
        grid_size : int
            4 for 4×4 zones, 8 for 8×8 zones
        add_noise : bool
            Enable realistic noise simulation
        unit : str
            'mm' or 'cm' for output distances
        rays_per_zone : int
            Number of sub-rays per zone (1, 4, 9, 16, 25 for 1×1, 2×2, 3×3, 4×4, 5×5)
            Higher values = more realistic SPAD array simulation, better detection coverage
        """
        self.position = np.array(position)
        self.direction = np.array(direction) / np.linalg.norm(direction)
        self.grid_size = grid_size
        self.add_noise = add_noise
        self.unit = unit
        self.rays_per_zone = rays_per_zone

        # Calculate sub-ray grid size (e.g., 9 -> 3×3, 16 -> 4×4)
        self.sub_grid_size = int(np.sqrt(rays_per_zone))
        if self.sub_grid_size ** 2 != rays_per_zone:
            raise ValueError(f"rays_per_zone must be a perfect square (1, 4, 9, 16, 25, ...), got {rays_per_zone}")

        # VL53L5CX specifications from datasheet
        self.fov_horizontal = np.radians(45)     # 45 degrees
        self.fov_vertical = np.radians(45)       # 45 degrees
        self.max_range = 4000                    # mm
        self.min_range = 20                      # mm

        # Accuracy specifications (from datasheet Table 19)
        self.accuracy_short_range = 15           # mm, for 20-200 mm range
        self.accuracy_long_range_pct = 0.045     # ±4.5% for 201-4000 mm

    def add_measurement_noise(self, distance_mm):
        """
        Add realistic measurement noise based on VL53L5CX accuracy specs.

        According to datasheet (Table 19):
        - 20-200 mm: ±15 mm accuracy
        - 201-4000 mm: ±4-5% accuracy (using 4.5%)
        """
        if distance_mm is None:
            return None

        if not self.add_noise:
            return distance_mm

        # Check valid range
        if distance_mm < self.min_range or distance_mm > self.max_range:
            return None

        # Apply noise based on distance range
        if distance_mm < 200:
            # Short range: ±15 mm uniform noise
            noise = np.random.uniform(-15, 15)
        else:
            # Long range: ±4.5% noise
            noise = np.random.uniform(-1, 1) * distance_mm * self.accuracy_long_range_pct

        noisy_distance = distance_mm + noise

        # Ensure result stays within valid range
        return np.clip(noisy_distance, self.min_range, self.max_range)

    def generate_beam_directions(self):
        """
        Generate beam directions for the grid pattern.
        Uses 45° H and 45° V FoV as per datasheet.

        Returns
        -------
        zone_beams : list of dict
            Each dict contains:
            - 'zone_index': Zone index (0 to grid_size^2 - 1)
            - 'beam_directions': List of ray directions for this zone
            - 'center_direction': Center ray direction for the zone
        """
        # Create orthogonal basis
        if abs(self.direction[0]) < 0.9:
            perpendicular = np.cross(self.direction, np.array([1, 0, 0]))
        else:
            perpendicular = np.cross(self.direction, np.array([0, 1, 0]))

        perpendicular = perpendicular / np.linalg.norm(perpendicular)
        perpendicular2 = np.cross(self.direction, perpendicular)
        perpendicular2 = perpendicular2 / np.linalg.norm(perpendicular2)

        zone_beams = []

        # Calculate FoV offsets
        max_offset_h = np.tan(self.fov_horizontal / 2)
        max_offset_v = np.tan(self.fov_vertical / 2)

        # Angular extent per zone
        zone_extent_h = 2 * max_offset_h / self.grid_size
        zone_extent_v = 2 * max_offset_v / self.grid_size

        # Generate grid of zones
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                zone_idx = i * self.grid_size + j

                # Center of this zone
                u_center = (i / (self.grid_size - 1) - 0.5) * 2 * max_offset_h
                v_center = (j / (self.grid_size - 1) - 0.5) * 2 * max_offset_v

                # Generate sub-rays within this zone
                sub_rays = []

                if self.rays_per_zone == 1:
                    # Single ray at zone center (original behavior)
                    beam_dir = self.direction + u_center * perpendicular + v_center * perpendicular2
                    beam_dir = beam_dir / np.linalg.norm(beam_dir)
                    sub_rays.append(beam_dir)
                else:
                    # Multiple sub-rays in a grid pattern within the zone
                    for si in range(self.sub_grid_size):
                        for sj in range(self.sub_grid_size):
                            # Sub-ray offset within zone (centered around zone center)
                            u_offset = (si / (self.sub_grid_size - 1) - 0.5) * zone_extent_h if self.sub_grid_size > 1 else 0
                            v_offset = (sj / (self.sub_grid_size - 1) - 0.5) * zone_extent_v if self.sub_grid_size > 1 else 0

                            u_total = u_center + u_offset
                            v_total = v_center + v_offset

                            beam_dir = self.direction + u_total * perpendicular + v_total * perpendicular2
                            beam_dir = beam_dir / np.linalg.norm(beam_dir)
                            sub_rays.append(beam_dir)

                # Center direction
                center_dir = self.direction + u_center * perpendicular + v_center * perpendicular2
                center_dir = center_dir / np.linalg.norm(center_dir)

                zone_beams.append({
                    'zone_index': zone_idx,
                    'beam_directions': sub_rays,
                    'center_direction': center_dir
                })

        return zone_beams

    def flip_zone_mapping(self, raw_results):
        """
        Apply VL53L5CX lens flipping transformation.

        According to datasheet section 5.1.3 (Effective zone orientation):
        "The zone identified as zone 0 in the bottom left of the SPAD array 
         is illuminated by a target located at the top right hand side of the scene."

        This means:
        - Horizontal flip: col -> (grid_size - 1 - col)
        - Vertical flip: row -> (grid_size - 1 - row)
        """
        flipped_results = []

        for result in raw_results:
            beam_idx = result['beam_index']
            row = beam_idx // self.grid_size
            col = beam_idx % self.grid_size

            # Apply both horizontal and vertical flip
            new_row = (self.grid_size - 1) - row
            new_col = (self.grid_size - 1) - col

            new_zone_id = new_row * self.grid_size + new_col

            flipped_result = result.copy()
            flipped_result['beam_index'] = new_zone_id
            flipped_result['zone_id'] = new_zone_id
            flipped_result['raw_beam_index'] = beam_idx

            flipped_results.append(flipped_result)

        # Sort by zone ID for proper ordering
        flipped_results.sort(key=lambda x: x['zone_id'])

        return flipped_results

    def scan(self, objects):
        """
        Perform complete scan with realistic VL53L5CX behavior.

        Returns
        -------
        flipped_results : list
            Sensor output after lens flipping (what user reads)
        raw_results : list
            Raw ray casting results before flipping (internal state)
        """
        zone_beams = self.generate_beam_directions()
        raw_results = []

        # Ray cast to find intersections for each zone
        for zone_data in zone_beams:
            zone_idx = zone_data['zone_index']
            sub_rays = zone_data['beam_directions']
            center_dir = zone_data['center_direction']

            # Cast all sub-rays for this zone
            detected_distances = []

            for sub_ray in sub_rays:
                min_dist_for_ray = None

                for obj in objects:
                    distance = obj.intersect_ray(self.position, sub_ray)

                    if distance is not None:
                        if min_dist_for_ray is None or distance < min_dist_for_ray:
                            min_dist_for_ray = distance

                if min_dist_for_ray is not None:
                    detected_distances.append(min_dist_for_ray)

            # Aggregate: Use closest distance (mimics real SPAD behavior - first photon return)
            if detected_distances:
                zone_distance = min(detected_distances)
            else:
                zone_distance = None

            # Convert to mm and add noise
            if zone_distance is not None:
                distance_mm = zone_distance * 10 if self.unit == 'cm' else zone_distance
                distance_mm = self.add_measurement_noise(distance_mm)

                # Convert back to original units
                if self.unit == 'cm':
                    zone_distance = distance_mm / 10 if distance_mm else None
                else:
                    zone_distance = distance_mm

            raw_results.append({
                'beam_index': zone_idx,
                'beam_direction': center_dir,  # Use center direction for visualization
                'all_sub_rays': sub_rays,  # Store all sub-rays for advanced visualization
                'distance': zone_distance,
                'distance_mm': zone_distance * 10 if self.unit == 'cm' and zone_distance else zone_distance,
                'num_sub_rays': len(sub_rays),
                'num_detections': len(detected_distances)
            })

        # Apply lens flipping (most important realistic feature)
        flipped_results = self.flip_zone_mapping(raw_results)

        return flipped_results, raw_results


# ============================================================================
# Visualization Functions
# ============================================================================

def plot_distance_grid(results, grid_size, ax=None):
    """
    Plot distance measurements as a 2D heatmap grid.

    Parameters
    ----------
    results : list
        Sensor scan results
    grid_size : int
        Grid size (4 or 8)
    ax : matplotlib axis, optional
        Axis to plot on. Creates new figure if None.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))

    # Create distance grid
    distance_grid = np.full((grid_size, grid_size), np.nan)

    for result in results:
        zone_id = result['zone_id']
        row = zone_id // grid_size
        col = zone_id % grid_size

        if result['distance'] is not None:
            distance_grid[row, col] = result['distance']

    # Plot heatmap
    im = ax.imshow(distance_grid, cmap='viridis_r', interpolation='nearest', origin='lower')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Distance (mm)', rotation=270, labelpad=20)

    # Add text annotations
    for i in range(grid_size):
        for j in range(grid_size):
            zone_id = i * grid_size + j
            if not np.isnan(distance_grid[i, j]):
                text = f'{distance_grid[i, j]:.0f}\nZ{zone_id}'
                ax.text(j, i, text, ha='center', va='center', color='white', fontsize=9, weight='bold')
            else:
                text = f'-\nZ{zone_id}'
                ax.text(j, i, text, ha='center', va='center', color='gray', fontsize=9)

    ax.set_title(f'VL53L5CX {grid_size}x{grid_size} Distance Heatmap\n(Zone 0 = Bottom-Left)', fontsize=12)
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')
    ax.set_xticks(range(grid_size))
    ax.set_yticks(range(grid_size))
    ax.grid(False)


def visualize_sensor_output(sensor, objects, results, show_rays=True, show_sub_rays=False, ray_length=300):
    """
    Visualize sensor output with 3D scene and distance heatmap.

    Parameters
    ----------
    sensor : VL53L5CXSensor
        Sensor instance
    objects : list
        List of 3D objects in scene
    results : list
        Sensor scan results (flipped)
    show_rays : bool
        Show sensor rays in 3D plot
    show_sub_rays : bool
        Show all sub-rays per zone (if rays_per_zone > 1)
    ray_length : float
        Maximum ray visualization length (mm)
    """
    fig = plt.figure(figsize=(16, 7))

    # ====== 3D Scene Plot ======
    ax1 = fig.add_subplot(121, projection='3d')
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Y (mm)')
    ax1.set_zlabel('Z (mm)')

    # Update title to show rays_per_zone info
    title = f'3D Scene with Sensor ({sensor.rays_per_zone} ray{"s" if sensor.rays_per_zone > 1 else ""}/zone)'
    ax1.set_title(title, fontsize=12, weight='bold')

    # Plot sensor
    ax1.scatter(*sensor.position, color='red', s=150, marker='^', label='Sensor', edgecolors='black', linewidths=2)

    # Plot objects
    for obj in objects:
        if isinstance(obj, Sphere):
            # Draw sphere
            u = np.linspace(0, 2 * np.pi, 30)
            v = np.linspace(0, np.pi, 30)
            x = obj.center[0] + obj.radius * np.outer(np.cos(u), np.sin(v))
            y = obj.center[1] + obj.radius * np.outer(np.sin(u), np.sin(v))
            z = obj.center[2] + obj.radius * np.outer(np.ones(np.size(u)), np.cos(v))
            ax1.plot_surface(x, y, z, alpha=0.4, color='dodgerblue', edgecolor='none')

        elif isinstance(obj, Cube):
            # Draw cube
            r = obj.size / 2
            vertices = np.array([
                [-r, -r, -r], [r, -r, -r], [r, r, -r], [-r, r, -r],
                [-r, -r, r], [r, -r, r], [r, r, r], [-r, r, r]
            ]) + obj.center

            faces = [
                [vertices[0], vertices[1], vertices[2], vertices[3]],
                [vertices[4], vertices[5], vertices[6], vertices[7]],
                [vertices[0], vertices[1], vertices[5], vertices[4]],
                [vertices[2], vertices[3], vertices[7], vertices[6]],
                [vertices[0], vertices[3], vertices[7], vertices[4]],
                [vertices[1], vertices[2], vertices[6], vertices[5]]
            ]

            ax1.add_collection3d(Poly3DCollection(faces, alpha=0.4, facecolor='cyan', edgecolor='black', linewidths=1))

    # Plot sensor rays
    if show_rays:
        for result in results:
            # Show sub-rays if requested and available
            if show_sub_rays and 'all_sub_rays' in result and len(result['all_sub_rays']) > 1:
                # Draw all sub-rays for this zone
                for sub_ray in result['all_sub_rays']:
                    distance = result['distance'] if result['distance'] is not None else ray_length
                    distance = min(distance, ray_length)
                    end_point = sensor.position + sub_ray * distance

                    if result['distance'] is not None:
                        color = 'lime'
                        alpha = 0.3
                        linewidth = 0.5
                    else:
                        color = 'gray'
                        alpha = 0.1
                        linewidth = 0.3

                    ax1.plot([sensor.position[0], end_point[0]],
                            [sensor.position[1], end_point[1]],
                            [sensor.position[2], end_point[2]],
                            color=color, alpha=alpha, linewidth=linewidth)
            else:
                # Draw center ray only
                beam_dir = result['beam_direction']
                distance = result['distance'] if result['distance'] is not None else ray_length
                distance = min(distance, ray_length)
                end_point = sensor.position + beam_dir * distance

                if result['distance'] is not None:
                    color = 'lime'
                    alpha = 0.7
                    linewidth = 1.5
                else:
                    color = 'gray'
                    alpha = 0.2
                    linewidth = 0.5

                ax1.plot([sensor.position[0], end_point[0]],
                        [sensor.position[1], end_point[1]],
                        [sensor.position[2], end_point[2]],
                        color=color, alpha=alpha, linewidth=linewidth)

    # Set axis limits
    all_points = [sensor.position]
    for obj in objects:
        if isinstance(obj, (Sphere, Cube)):
            all_points.append(obj.center)

    if all_points:
        all_points = np.array(all_points)
        margin = 80
        ax1.set_xlim([all_points[:, 0].min() - margin, all_points[:, 0].max() + margin])
        ax1.set_ylim([all_points[:, 1].min() - margin, all_points[:, 1].max() + margin])
        ax1.set_zlim([0, all_points[:, 2].max() + margin])

    ax1.legend(loc='upper left')
    ax1.view_init(elev=20, azim=45)

    # ====== Distance Heatmap ======
    ax2 = fig.add_subplot(122)
    plot_distance_grid(results, sensor.grid_size, ax=ax2)

    plt.tight_layout()
    plt.show()


# ============================================================================
# Demo and Testing
# ============================================================================

def main():
    print("=" * 80)
    print("VL53L5CX Time-of-Flight Sensor Realistic Simulator")
    print("=" * 80)
    print("\nBased on STMicroelectronics VL53L5CX Datasheet (DS13754 - Rev 5)")
    print("\nKey Features Implemented:")
    print("  + Field of View: 45 deg H x 45 deg V (63 deg diagonal)")
    print("  + Lens Flipping: Horizontal and vertical image inversion")
    print("  + Accurate Zone Mapping: Zone 0 at bottom-left sees top-right scene")
    print("  + Realistic Noise: +/-15 mm (20-200 mm), +/-4.5% (201-4000 mm)")
    print("  + Range Limits: 20-4000 mm")
    print("\n" + "=" * 80)

    # Test 1: Sphere detection
    print("\nTest 1: Sphere Detection with Noise")
    print("-" * 80)

    sphere = Sphere(center=[0, 0, 50], radius=50)
    sensor = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=4,
        add_noise=True,
        unit='mm'
    )

    flipped, raw = sensor.scan([sphere])

    print(f"\nConfiguration:")
    print(f"  Position: {sensor.position} mm")
    print(f"  Direction: {sensor.direction}")
    print(f"  FoV: {np.degrees(sensor.fov_horizontal):.0f} deg H x {np.degrees(sensor.fov_vertical):.0f} deg V")
    print(f"  Noise: ENABLED (realistic)")

    print(f"\nVL53L5CX Sensor Output (After Lens Flipping):")
    print(f"{'Zone':>4} {'Detected':>12} {'Type':>20}")
    print("-" * 40)

    for result in flipped:
        if result['distance'] is not None:
            dist_str = f"{result['distance']:.1f} mm"
            result_type = "Object detected"
        else:
            dist_str = "-"
            result_type = "No target"

        print(f"{result['zone_id']:4d} {dist_str:>12} {result_type:>20}")

    print("\n" + "=" * 80)

    # Test 2: Cube detection
    print("\nTest 2: Cube Detection (No Noise - Ideal)")
    print("-" * 80)

    cube = Cube(center=[0, 0, 150], size=40)
    sensor_ideal = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=4,
        add_noise=False,  # Ideal measurements
        unit='mm'
    )

    flipped2, raw2 = sensor_ideal.scan([cube])

    print(f"\nConfiguration:")
    print(f"  Position: {sensor_ideal.position} mm")
    print(f"  Noise: DISABLED (ideal/exact)")

    print(f"\nVL53L5CX Sensor Output:")
    print(f"{'Zone':>4} {'Distance':>12} {'Status':>20}")
    print("-" * 40)

    for result in flipped2:
        if result['distance'] is not None:
            dist_str = f"{result['distance']:.1f} mm"
            status = "+ Detected"
        else:
            dist_str = "Out of range"
            status = "- No signal"

        print(f"{result['zone_id']:4d} {dist_str:>12} {status:>20}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
