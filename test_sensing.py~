"""
VL53L5CX Sensor Test Scenes
Test configurations for validating the sensor simulator with different scenarios.
"""

from vl53l5cx_realistic_simulator import (
    VL53L5CXSensor,
    Sphere,
    Cube,
    Plane,
    visualize_sensor_output
)


def scene_1_simple_sphere():
    """Scene 1: Single sphere detection (basic validation)"""
    print("\n" + "="*80)
    print("SCENE 1: Single Sphere Detection")
    print("="*80)

    # Create sensor
    sensor = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=4,
        add_noise=True,
        unit='mm'
    )

    # Create sphere
    sphere = Sphere(center=[0, 0, 200], radius=50)
    objects = [sphere]

    # Scan
    flipped_results, raw_results = sensor.scan(objects)

    # Print results
    print(f"\nSensor: Position={sensor.position}, Direction={sensor.direction}")
    print(f"Object: Sphere at {sphere.center}, radius={sphere.radius} mm")
    print(f"\nDetections: {sum(1 for r in flipped_results if r['distance'] is not None)}/16 zones")

    # Visualize
    visualize_sensor_output(sensor, objects, flipped_results)


def scene_2_cube_detection():
    """Scene 2: Cube detection"""
    print("\n" + "="*80)
    print("SCENE 2: Cube Detection")
    print("="*80)

    # Create sensor
    sensor = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=4,
        add_noise=False,  # No noise for cleaner cube edges
        unit='mm'
    )

    # Create cube
    cube = Cube(center=[0, 0, 300], size=80)
    objects = [cube]

    # Scan
    flipped_results, raw_results = sensor.scan(objects)

    # Print results
    print(f"\nSensor: Position={sensor.position}, Grid={sensor.grid_size}x{sensor.grid_size}")
    print(f"Object: Cube at {cube.center}, size={cube.size} mm")
    print(f"\nDetections: {sum(1 for r in flipped_results if r['distance'] is not None)}/16 zones")

    # Visualize
    visualize_sensor_output(sensor, objects, flipped_results)


def scene_3_multiple_objects():
    """Scene 3: Multiple objects at different distances"""
    print("\n" + "="*80)
    print("SCENE 3: Multiple Objects")
    print("="*80)

    # Create sensor
    sensor = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=8,  # Higher resolution
        add_noise=True,
        unit='mm'
    )

    # Create multiple objects
    sphere1 = Sphere(center=[-50, -50, 250], radius=30)
    sphere2 = Sphere(center=[50, 50, 350], radius=40)
    cube = Cube(center=[0, -60, 400], size=50)
    objects = [sphere1, sphere2, cube]

    # Scan
    flipped_results, raw_results = sensor.scan(objects)

    # Print results
    print(f"\nSensor: Position={sensor.position}, Grid={sensor.grid_size}x{sensor.grid_size}")
    print(f"Objects:")
    print(f"  - Sphere 1: center={sphere1.center}, radius={sphere1.radius} mm")
    print(f"  - Sphere 2: center={sphere2.center}, radius={sphere2.radius} mm")
    print(f"  - Cube: center={cube.center}, size={cube.size} mm")
    print(f"\nDetections: {sum(1 for r in flipped_results if r['distance'] is not None)}/64 zones")

    # Visualize
    visualize_sensor_output(sensor, objects, flipped_results, ray_length=500)


def scene_4_range_limits():
    """Scene 4: Testing sensor range limits (min/max range)"""
    print("\n" + "="*80)
    print("SCENE 4: Range Limits Test")
    print("="*80)

    # Create sensor
    sensor = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=4,
        add_noise=False,
        unit='mm'
    )

    # Create objects at various ranges
    # Too close (< 20mm) - should not detect
    sphere_too_close = Sphere(center=[0, 0, 10], radius=5)

    # At min range (20mm) - should detect
    sphere_min_range = Sphere(center=[30, 30, 25], radius=8)

    # In good range
    sphere_good_range = Sphere(center=[-30, -30, 500], radius=40)

    # Far range (near 4000mm) - should detect
    plane_far = Plane(point=[0, 0, 3800], normal=[0, 0, -1])

    objects = [sphere_too_close, sphere_min_range, sphere_good_range, plane_far]

    # Scan
    flipped_results, raw_results = sensor.scan(objects)

    # Print results
    print(f"\nSensor Range: {sensor.min_range} - {sensor.max_range} mm")
    print(f"\nObjects:")
    print(f"  - Sphere (too close): z={sphere_too_close.center[2]} mm")
    print(f"  - Sphere (min range): z={sphere_min_range.center[2]} mm")
    print(f"  - Sphere (good range): z={sphere_good_range.center[2]} mm")
    print(f"  - Plane (far): z={plane_far.point[2]} mm")

    detections = [r['distance'] for r in flipped_results if r['distance'] is not None]
    if detections:
        print(f"\nDetected ranges: {min(detections):.0f} - {max(detections):.0f} mm")
    print(f"Total detections: {len(detections)}/16 zones")

    # Visualize
    visualize_sensor_output(sensor, objects, flipped_results, ray_length=4000)


def scene_5_multi_ray_comparison():
    """Scene 5: Compare 1-ray vs 9-ray per zone (improved detection)"""
    print("\n" + "="*80)
    print("SCENE 5: Multi-Ray Per Zone Comparison")
    print("="*80)

    # Create small spheres positioned off-center (between zone centers)
    # These demonstrate the improved detection with multi-ray sampling
    sphere1 = Sphere(center=[15, 15, 250], radius=20)   # Off-center
    sphere2 = Sphere(center=[-20, 10, 300], radius=18)  # Off-center
    sphere3 = Sphere(center=[10, -15, 350], radius=22)  # Off-center
    objects = [sphere1, sphere2, sphere3]

    # Test with 1 ray per zone (original)
    print("\n--- Test 1: Single Ray Per Zone (Original) ---")
    sensor_1ray = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=4,
        add_noise=False,
        unit='mm',
        rays_per_zone=1
    )

    flipped_1ray, raw_1ray = sensor_1ray.scan(objects)
    detections_1ray = sum(1 for r in flipped_1ray if r['distance'] is not None)

    print(f"Sensor: {sensor_1ray.grid_size}×{sensor_1ray.grid_size} grid, {sensor_1ray.rays_per_zone} ray/zone")
    print(f"Objects: 3 small spheres positioned off-center")
    print(f"Detections: {detections_1ray}/16 zones")

    # Test with 9 rays per zone (multi-ray SPAD simulation)
    print("\n--- Test 2: Multi-Ray Per Zone (Realistic SPAD) ---")
    sensor_9ray = VL53L5CXSensor(
        position=[0, 0, 0],
        direction=[0, 0, 1],
        grid_size=4,
        add_noise=False,
        unit='mm',
        rays_per_zone=9  # 3×3 sub-sampling
    )

    flipped_9ray, raw_9ray = sensor_9ray.scan(objects)
    detections_9ray = sum(1 for r in flipped_9ray if r['distance'] is not None)

    print(f"Sensor: {sensor_9ray.grid_size}×{sensor_9ray.grid_size} grid, {sensor_9ray.rays_per_zone} rays/zone")
    print(f"Objects: Same 3 small spheres")
    print(f"Detections: {detections_9ray}/16 zones")

    # Summary
    print("\n" + "-"*80)
    print("COMPARISON SUMMARY:")
    print(f"  1 ray/zone:  {detections_1ray} zones detected")
    print(f"  9 rays/zone: {detections_9ray} zones detected")
    print(f"  Improvement: +{detections_9ray - detections_1ray} zones ({((detections_9ray - detections_1ray) / 16 * 100):.1f}%)")
    print("\n  Multi-ray simulation better represents real SPAD array behavior,")
    print("  detecting objects within zone angular extent (not just center).")
    print("-"*80)

    # Visualize both
    print("\nVisualizing 1 ray/zone...")
    visualize_sensor_output(sensor_1ray, objects, flipped_1ray, ray_length=400)

    print("\nVisualizing 9 rays/zone (with sub-rays shown)...")
    visualize_sensor_output(sensor_9ray, objects, flipped_9ray, show_sub_rays=True, ray_length=400)


def run_all_scenes():
    """Run all test scenes sequentially"""
    print("\n" + "#"*80)
    print("# VL53L5CX SENSOR TEST SUITE")
    print("#"*80)

    scene_1_simple_sphere()
    scene_2_cube_detection()
    scene_3_multiple_objects()
    scene_4_range_limits()
    scene_5_multi_ray_comparison()

    print("\n" + "#"*80)
    print("# ALL TESTS COMPLETED")
    print("#"*80)


if __name__ == "__main__":
    # Run individual scene or all
    # Uncomment the scene you want to test:

    # scene_1_simple_sphere()
    # scene_2_cube_detection()
    # scene_3_multiple_objects()
    # scene_4_range_limits()
    # scene_5_multi_ray_comparison()

    # Or run all scenes:
    run_all_scenes()
