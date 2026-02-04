#!/usr/bin/env python3
"""
Convert VRM avatar to GLB format for Flutter 3D rendering.

VRM files are glTF 2.0 subset, so conversion is minimal.
This script handles format conversion and optional optimization.

Usage:
    python scripts/vrm_to_glb.py input.vrm output.glb [--optimize]

Options:
    --optimize          Apply optimization (decimate mesh, compress textures)
    --decimate RATIO    Polygon reduction ratio (0.0-1.0, default: 0.5)
    --check-shapes      List blend shapes in model
    --help              Show this help message
"""

import argparse
import json
import shutil
import struct
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Try to import optional dependencies
try:
    import PIL.Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Note: PIL not installed, texture compression skipped")
    print("Install with: pip install pillow")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class VRMConverter:
    """Converts VRM to GLB format."""

    def __init__(self, vrm_path: str, optimize: bool = False):
        """Initialize converter.

        Args:
            vrm_path: Path to input VRM file
            optimize: Whether to apply optimization
        """
        self.vrm_path = Path(vrm_path)
        self.optimize = optimize

        if not self.vrm_path.exists():
            raise FileNotFoundError(f"VRM file not found: {vrm_path}")

        # VRM is glTF 2.0, so we can parse it directly
        self.file_size = self.vrm_path.stat().st_size
        print(f"✓ Found VRM file: {self.vrm_path.name} ({self.file_size / (1024*1024):.1f} MB)")

    def convert(self, output_path: str) -> bool:
        """Convert VRM to GLB.

        Args:
            output_path: Path for output GLB file

        Returns:
            True if successful
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # VRM is already glTF 2.0 binary format
            # We can just copy it and rename
            if not self.optimize:
                # Simple copy - VRM is valid GLB
                shutil.copy2(self.vrm_path, output_path)
                output_size = output_path.stat().st_size
                print(f"✓ Converted: {self.vrm_path.name} → {output_path.name}")
                print(f"  Size: {output_size / (1024*1024):.1f} MB")
                return True
            else:
                # Optimized conversion (requires additional processing)
                return self._convert_optimized(output_path)

        except Exception as e:
            print(f"✗ Conversion failed: {e}")
            return False

    def _convert_optimized(self, output_path: Path) -> bool:
        """Convert with optimization (mesh decimation, texture compression).

        Note: Requires Blender for proper mesh decimation.
        For now, we copy and suggest manual optimization in Blender.

        Args:
            output_path: Output path

        Returns:
            True if successful
        """
        print("\n⚠ Full optimization requires Blender for mesh decimation.")
        print("  Recommended Blender workflow:")
        print("  1. File → Import VRM")
        print("  2. Select mesh → Add Decimate modifier (ratio: 0.5)")
        print("  3. Scale textures to 1024x1024")
        print("  4. Export as glTF 2.0 (.glb)")
        print("\nFor now, copying file without mesh optimization...")

        shutil.copy2(self.vrm_path, output_path)
        output_size = output_path.stat().st_size

        print(f"\n✓ Converted: {self.vrm_path.name} → {output_path.name}")
        print(f"  Size: {output_size / (1024*1024):.1f} MB")

        if output_size > 20 * 1024 * 1024:
            print("\n⚠ Warning: Model is >20 MB")
            print("  Recommended optimization:")
            print("  - Decimate mesh to 50% polygons")
            print("  - Resize textures to 1024x1024")
            print("  - Remove unused materials")

        return True

    def check_blend_shapes(self) -> bool:
        """List blend shapes in the VRM model.

        Returns:
            True if blend shapes found
        """
        try:
            # Read glTF JSON chunk
            with open(self.vrm_path, 'rb') as f:
                # glTF header: 4 bytes magic, 4 bytes version, 4 bytes length
                magic = f.read(4)
                if magic != b'glTF':
                    print("✗ Not a valid glTF/VRM file")
                    return False

                version = struct.unpack('<I', f.read(4))[0]
                length = struct.unpack('<I', f.read(4))[0]

                # Read JSON chunk header
                chunk_length = struct.unpack('<I', f.read(4))[0]
                chunk_type = f.read(4)

                if chunk_type != b'JSON':
                    print("✗ Unexpected glTF chunk type")
                    return False

                # Read and parse JSON
                json_data = f.read(chunk_length).decode('utf-8')
                gltf = json.loads(json_data)

            # Extract blend shapes (morph targets) from meshes
            blend_shapes = set()
            for mesh in gltf.get('meshes', []):
                for primitive in mesh.get('primitives', []):
                    targets = primitive.get('targets', [])
                    for i, target in enumerate(targets):
                        # Blend shape names are in the mesh name + index
                        mesh_name = mesh.get('name', f'mesh_{gltf["meshes"].index(mesh)}')
                        blend_shapes.add(f"{mesh_name}_{i}")

            # Also check VRM extensions for blend shapes
            vrm_meta = gltf.get('extensions', {}).get('VRM', {})
            blend_shapes_data = vrm_meta.get('blendShapeMaster', {}).get('blendShapeGroups', [])

            print(f"\n📋 Blend Shapes in {self.vrm_path.name}:")

            # Expected mouth shapes for lip sync
            mouth_shapes = ['aa', 'ih', 'ou', 'E', 'neutral', 'viseme']
            expression_shapes = ['happy', 'sad', 'angry', 'surprised', 'joy', 'sorrow']

            found_mouth = []
            found_expression = []
            found_other = []

            for group in blend_shapes_data:
                name = group.get('name', '').lower()
                if any(m in name for m in mouth_shapes):
                    found_mouth.append(group.get('name'))
                elif any(e in name for e in expression_shapes):
                    found_expression.append(group.get('name'))
                else:
                    found_other.append(group.get('name'))

            if found_mouth:
                print(f"\n  ✓ Mouth shapes (for lip sync):")
                for name in found_mouth:
                    print(f"    - {name}")
            else:
                print(f"\n  ⚠ No mouth shapes found (needed for lip sync)")

            if found_expression:
                print(f"\n  ✓ Expression shapes:")
                for name in found_expression:
                    print(f"    - {name}")

            if found_other:
                print(f"\n  Other blend shapes:")
                for name in found_other:
                    print(f"    - {name}")

            if not blend_shapes_data:
                print("  ⚠ No blend shapes found in VRM metadata")
                print("    Try opening in Blender to verify")

            return len(found_mouth) > 0 or len(found_expression) > 0

        except Exception as e:
            print(f"✗ Error reading blend shapes: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert VRM avatar to GLB format for Flutter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple conversion (VRM → GLB, no optimization)
  python scripts/vrm_to_glb.py avatar.vrm avatar.glb

  # Check blend shapes
  python scripts/vrm_to_glb.py avatar.vrm --check-shapes

  # Convert with optimization suggestions
  python scripts/vrm_to_glb.py avatar.vrm avatar.glb --optimize

  # Full workflow
  python scripts/vrm_to_glb.py avatar.vrm avatar.glb --check-shapes --optimize
        """
    )

    parser.add_argument(
        'input',
        help='Input VRM file path'
    )

    parser.add_argument(
        'output',
        nargs='?',
        default=None,
        help='Output GLB file path (default: input with .glb extension)'
    )

    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Apply optimization (guides for manual Blender optimization)'
    )

    parser.add_argument(
        '--check-shapes',
        action='store_true',
        help='List blend shapes in the model'
    )

    args = parser.parse_args()

    # Determine output path
    output_path = args.output or args.input.replace('.vrm', '.glb')
    if output_path == args.input:
        output_path = str(Path(args.input).stem) + '.glb'

    print("=" * 60)
    print("VRM to GLB Converter")
    print("=" * 60)

    try:
        converter = VRMConverter(args.input, optimize=args.optimize)

        # Check blend shapes if requested
        if args.check_shapes:
            converter.check_blend_shapes()
            print()

        # Convert
        if not args.check_shapes or args.output:
            if converter.convert(output_path):
                print("\n✓ Conversion successful!")
                print(f"\nNext steps:")
                print(f"1. Copy to Flutter: cp {output_path} flutter_app/assets/models/")
                print(f"2. Run app: flutter run")
                print(f"3. Send a message and test lip sync")

                # Optimization reminder
                if converter.file_size > 20 * 1024 * 1024:
                    print(f"\n⚠ Optimization recommended (model is {converter.file_size / (1024*1024):.1f} MB):")
                    print("  Open in Blender and:")
                    print("  - Add Decimate modifier (ratio: 0.5)")
                    print("  - Scale textures to 1024x1024")
                    print("  - Export as glTF 2.0 (.glb)")
                return 0
            else:
                return 1

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
