#!/usr/bin/env python3
"""
Generate Test Images for Benchmarking
======================================

Creates diverse synthetic images for comprehensive Tom Sawyer benchmarking:
- Different color palettes (warm, cool, neutral)
- Different complexities (gradients, patterns, natural-looking)
- Different sizes (512x512, 1024x1024)
"""

import numpy as np
import cv2
from pathlib import Path


def create_gradient_image(width: int, height: int, color1: tuple, color2: tuple) -> np.ndarray:
    """Create a smooth gradient image from color1 to color2."""
    image = np.zeros((height, width, 3), dtype=np.uint8)

    for i in range(height):
        # Vertical gradient
        ratio = i / height
        color = tuple(int(c1 * (1 - ratio) + c2 * ratio) for c1, c2 in zip(color1, color2))
        image[i, :] = color

    return image


def create_radial_gradient(width: int, height: int, center_color: tuple, edge_color: tuple) -> np.ndarray:
    """Create a radial gradient from center to edges."""
    image = np.zeros((height, width, 3), dtype=np.uint8)

    center_x, center_y = width // 2, height // 2
    max_distance = np.sqrt(center_x**2 + center_y**2)

    for y in range(height):
        for x in range(width):
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            ratio = min(distance / max_distance, 1.0)
            color = tuple(int(c1 * (1 - ratio) + c2 * ratio) for c1, c2 in zip(center_color, edge_color))
            image[y, x] = color

    return image


def create_pattern_image(width: int, height: int, base_color: tuple, pattern_color: tuple) -> np.ndarray:
    """Create an image with geometric patterns."""
    image = np.full((height, width, 3), base_color, dtype=np.uint8)

    # Add circles
    for i in range(5):
        center = (np.random.randint(0, width), np.random.randint(0, height))
        radius = np.random.randint(30, 100)
        cv2.circle(image, center, radius, pattern_color, -1)

    # Add rectangles
    for i in range(3):
        pt1 = (np.random.randint(0, width - 100), np.random.randint(0, height - 100))
        pt2 = (pt1[0] + np.random.randint(50, 150), pt1[1] + np.random.randint(50, 150))
        cv2.rectangle(image, pt1, pt2, pattern_color, -1)

    # Add some noise for texture
    noise = np.random.randint(-20, 20, (height, width, 3), dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return image


def create_natural_scene(width: int, height: int, sky_color: tuple, ground_color: tuple) -> np.ndarray:
    """Create a natural-looking scene with sky and ground."""
    image = np.zeros((height, width, 3), dtype=np.uint8)

    # Sky gradient (top half)
    horizon = height // 2
    for i in range(horizon):
        ratio = i / horizon
        color = tuple(int(c1 * (1 - ratio) + c2 * ratio) for c1, c2 in zip(sky_color, (200, 220, 255)))
        image[i, :] = color

    # Ground gradient (bottom half)
    for i in range(horizon, height):
        ratio = (i - horizon) / (height - horizon)
        color = tuple(int(c1 * (1 - ratio) + c2 * ratio) for c1, c2 in zip(ground_color, (50, 80, 40)))
        image[i, :] = color

    # Add clouds (white circles with blur)
    cloud_layer = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(8):
        center = (np.random.randint(0, width), np.random.randint(0, horizon))
        radius = np.random.randint(30, 80)
        cv2.circle(cloud_layer, center, radius, (255, 255, 255), -1)

    cloud_layer = cv2.GaussianBlur(cloud_layer, (51, 51), 0)
    image = cv2.addWeighted(image, 0.8, cloud_layer, 0.2, 0)

    # Add trees (dark green triangles)
    for i in range(5):
        base_x = np.random.randint(50, width - 50)
        base_y = horizon + np.random.randint(20, 100)
        tree_height = np.random.randint(60, 120)

        pts = np.array([
            [base_x, base_y],
            [base_x - 30, base_y + tree_height],
            [base_x + 30, base_y + tree_height]
        ], np.int32)
        cv2.fillPoly(image, [pts], (20, 100, 30))

    return image


def main():
    """Generate test image suite."""
    output_dir = Path("test_images")
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("GENERATING TEST IMAGES FOR TOM SAWYER BENCHMARKING")
    print("=" * 70)

    # Define color palettes
    palettes = {
        "warm_sunset": {
            "gradient": ((255, 180, 100), (200, 80, 50)),
            "radial": ((255, 200, 120), (180, 60, 40)),
            "pattern_base": (220, 150, 80),
            "pattern_accent": (180, 80, 40),
            "sky": (255, 150, 100),
            "ground": (150, 100, 60),
        },
        "cool_ocean": {
            "gradient": ((100, 200, 255), (50, 100, 200)),
            "radial": ((120, 220, 255), (40, 80, 180)),
            "pattern_base": (80, 180, 220),
            "pattern_accent": (40, 100, 180),
            "sky": (100, 180, 255),
            "ground": (60, 120, 150),
        },
        "neutral_gray": {
            "gradient": ((200, 200, 200), (80, 80, 80)),
            "radial": ((220, 220, 220), (60, 60, 60)),
            "pattern_base": (180, 180, 180),
            "pattern_accent": (100, 100, 100),
            "sky": (200, 200, 200),
            "ground": (120, 120, 120),
        },
        "vibrant_spring": {
            "gradient": ((180, 255, 150), (100, 200, 80)),
            "radial": ((200, 255, 180), (80, 180, 60)),
            "pattern_base": (150, 220, 120),
            "pattern_accent": (80, 160, 60),
            "sky": (150, 220, 200),
            "ground": (80, 180, 60),
        },
    }

    sizes = [
        (512, 512, "512x512"),
        (1024, 1024, "1024x1024"),
    ]

    image_types = [
        ("gradient", create_gradient_image, ["gradient"]),
        ("radial", create_radial_gradient, ["radial"]),
        ("pattern", create_pattern_image, ["pattern_base", "pattern_accent"]),
        ("natural", create_natural_scene, ["sky", "ground"]),
    ]

    total_images = 0

    for palette_name, palette_colors in palettes.items():
        print(f"\n[{palette_name.upper()}]")

        for img_type, create_func, color_keys in image_types:
            for width, height, size_label in sizes:
                # Extract colors for this image type
                if len(color_keys) == 1:
                    # For gradient/radial, the value is already a tuple of colors
                    colors = palette_colors[color_keys[0]]
                else:
                    # For pattern/natural, extract individual color keys
                    colors = tuple(palette_colors[key] for key in color_keys)

                # Create image
                image = create_func(width, height, *colors)

                # Save image
                filename = f"{palette_name}_{img_type}_{size_label}.jpg"
                filepath = output_dir / filename
                cv2.imwrite(str(filepath), image)

                total_images += 1
                print(f"  ✓ Created: {filename}")

    print(f"\n{'=' * 70}")
    print(f"Generated {total_images} test images in {output_dir}/")
    print(f"{'=' * 70}\n")

    # Create pairs file for benchmarking
    pairs_file = output_dir / "benchmark_pairs.txt"
    with open(pairs_file, "w") as f:
        f.write("# Source,Target pairs for benchmarking\n")
        f.write("# Format: source_image,target_image\n\n")

        # Create interesting cross-palette pairs
        pairs = [
            ("warm_sunset_gradient_512x512.jpg", "cool_ocean_gradient_512x512.jpg"),
            ("cool_ocean_radial_512x512.jpg", "vibrant_spring_radial_512x512.jpg"),
            ("neutral_gray_pattern_512x512.jpg", "warm_sunset_pattern_512x512.jpg"),
            ("vibrant_spring_natural_512x512.jpg", "cool_ocean_natural_512x512.jpg"),
            ("warm_sunset_gradient_1024x1024.jpg", "neutral_gray_gradient_1024x1024.jpg"),
        ]

        for source, target in pairs:
            f.write(f"{source},{target}\n")

    print(f"Created benchmark pairs configuration: {pairs_file}")


if __name__ == "__main__":
    main()
