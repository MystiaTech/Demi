# VRM Avatar - Quick Start Guide

Since you already have a `.vrm` file, here's the fastest path to a working avatar.

---

## Option 1: Direct VRM (Fastest - 5 minutes) ✨

**VRM files are glTF 2.0 format, so they work directly with flutter_3d_controller!**

### Step 1: Copy VRM to Flutter Assets

```bash
mkdir -p flutter_app/assets/models
cp your_avatar.vrm flutter_app/assets/models/demi.vrm
```

### Step 2: Update pubspec.yaml

```yaml
flutter:
  assets:
    - assets/models/demi.vrm   # VRM support
    - assets/models/demi.glb   # GLB fallback (optional)
    - assets/images/
    - assets/animations/
```

### Step 3: Code Already Supports It!

The `avatar_display_3d.dart` now has:
- **Primary format**: `.vrm` (your file)
- **Fallback format**: `.glb` (converted, if needed)
- **Auto-fallback**: If VRM fails to load, tries GLB automatically

**Constructor defaults:**
```dart
const AvatarDisplay3D(
  ...
  modelPath: 'assets/models/demi.vrm',        // ← Primary
  fallbackModelPath: 'assets/models/demi.glb', // ← Fallback
)
```

### Step 4: Test It

```bash
cd flutter_app
flutter run
```

**Expected result:**
- Loading spinner appears
- Avatar loads after 2-3 seconds
- Send a message and watch mouth animate ✨

---

## Option 2: Convert to GLB (Better Performance)

If you want optimized GLB format, use the conversion script:

```bash
# Check blend shapes first
python scripts/vrm_to_glb.py your_avatar.vrm --check-shapes

# Output:
# ✓ Found VRM file: your_avatar.vrm (45.3 MB)
#
# 📋 Blend Shapes in your_avatar.vrm:
#   ✓ Mouth shapes (for lip sync):
#     - Viseme_aa
#     - Viseme_ih
#     - ... etc

# Convert to GLB
python scripts/vrm_to_glb.py your_avatar.vrm flutter_app/assets/models/demi.glb

# Output:
# ✓ Converted: your_avatar.vrm → demi.glb
#   Size: 45.3 MB
# ⚠ Model is >20 MB - optimization recommended
```

**If file is >20 MB, optimize in Blender:**

1. **File → Import → glTF**
2. **Select mesh → Modifiers → Add Decimate**
   - Ratio: 0.5 (reduces polygons to 50%)
   - Apply modifier
3. **Scale textures to 1024x1024**
   - Image Editor → Select all → Scale Image
4. **File → Export → glTF 2.0 (.glb)**
5. **Copy optimized to flutter_app/assets/models/demi.glb**

---

## Troubleshooting: VRM Not Loading

**If you see "Failed to load avatar":**

### Check 1: File Path
```bash
# Verify file exists in correct location
ls -la flutter_app/assets/models/demi.vrm
# Should output file info

# Check pubspec.yaml includes it
cat flutter_app/pubspec.yaml | grep models
```

### Check 2: Update pubspec.yaml

```yaml
flutter:
  uses-material-design: true

  assets:
    - assets/models/demi.vrm  # ← Add this line
    - assets/models/
    - assets/images/
    - assets/animations/
```

### Check 3: Clean Flutter Cache

```bash
cd flutter_app
flutter clean
flutter pub get
flutter run
```

### Check 4: Use Fallback

If VRM isn't supported by `flutter_3d_controller`, convert to GLB:

```bash
python scripts/vrm_to_glb.py your_avatar.vrm flutter_app/assets/models/demi.glb
# Will auto-fallback to this if VRM fails
```

---

## Checking Blend Shapes

Before testing, verify your model has the required mouth shapes:

```bash
python scripts/vrm_to_glb.py your_avatar.vrm --check-shapes

# Output example:
# 📋 Blend Shapes in your_avatar.vrm:
#   ✓ Mouth shapes (for lip sync):
#     - Viseme_aa
#     - Viseme_ih
#     - Viseme_ou
#     - Viseme_E
#     - Viseme_neutral
#   ✓ Expression shapes:
#     - Happy
#     - Sad
#     - Angry
#     - Surprised
```

**If mouth shapes are named differently:**
- Note the actual names
- Update `flutter_app/lib/widgets/avatar_display_3d.dart`
- In `_onVisemeChanged()` method:

```dart
void _onVisemeChanged(String viseme, double weight) {
  // Map to your model's actual blend shape names
  const visemeToBlendShape = {
    'aa': 'YOUR_ACTUAL_AA_NAME',      // ← Update these
    'ih': 'YOUR_ACTUAL_IH_NAME',
    'ou': 'YOUR_ACTUAL_OU_NAME',
    'E': 'YOUR_ACTUAL_E_NAME',
    'neutral': 'YOUR_ACTUAL_NEUTRAL_NAME',
  };
  // ... rest of method
}
```

---

## Full Workflow

### For VRM Only (Fastest)
```bash
# 1. Check blend shapes
python scripts/vrm_to_glb.py your_avatar.vrm --check-shapes

# 2. Copy to Flutter
cp your_avatar.vrm flutter_app/assets/models/demi.vrm

# 3. Update blend shape names if needed
# Edit: flutter_app/lib/widgets/avatar_display_3d.dart

# 4. Test
cd flutter_app
flutter run
```

### For VRM + GLB Fallback (Recommended)
```bash
# 1. Check and convert
python scripts/vrm_to_glb.py your_avatar.vrm flutter_app/assets/models/demi.glb --check-shapes

# 2. Copy VRM as well
cp your_avatar.vrm flutter_app/assets/models/demi.vrm

# 3. Update blend shape names if needed

# 4. Test
cd flutter_app
flutter run
```

### For Optimized GLB Only (Best Performance)
```bash
# 1. Convert
python scripts/vrm_to_glb.py your_avatar.vrm flutter_app/assets/models/demi.glb --check-shapes

# 2. Optimize in Blender (if >20 MB):
#    - Open demi.glb
#    - Add Decimate modifier (0.5 ratio)
#    - Scale textures to 1024
#    - Export as .glb
#    - Save back to flutter_app/assets/models/demi.glb

# 3. Update modelPath in code if desired
# lib/widgets/avatar_display_3d.dart:
# modelPath: 'assets/models/demi.glb'

# 4. Test
cd flutter_app
flutter run
```

---

## Quick Command Reference

```bash
# Check blend shapes in VRM
python scripts/vrm_to_glb.py avatar.vrm --check-shapes

# Convert VRM to GLB
python scripts/vrm_to_glb.py avatar.vrm output.glb

# Copy to Flutter
cp avatar.vrm flutter_app/assets/models/demi.vrm
cp output.glb flutter_app/assets/models/demi.glb

# Clean and run
cd flutter_app && flutter clean && flutter pub get && flutter run

# Profile performance
flutter run --profile
```

---

## Expected Timeline

- **Copy VRM file**: 1 min
- **Check blend shapes**: 2 min
- **Update blend shape names (if needed)**: 5 min
- **First test run**: 3-5 min
- **Debug/troubleshoot**: 5-10 min

**Total: 15-30 minutes for working avatar** ✨

---

## Success Indicators

When it's working, you should see:

1. ✅ App loads without crashes
2. ✅ Avatar appears in 2-3 seconds
3. ✅ "Start a conversation with Demi! 💬" message visible
4. ✅ Avatar is visible above message list
5. ✅ Type a message and press send
6. ✅ Avatar mouth moves as TTS audio plays
7. ✅ Mouth shapes sync with audio (natural feeling)
8. ✅ Avatar breathes subtly (chest sway)
9. ✅ Avatar blinks randomly
10. ✅ Expression changes based on emotion

---

## Next Steps After Basic Test

1. **Profile performance**
   ```bash
   flutter run --profile
   # Check DevTools for FPS, memory
   ```

2. **Test on real device**
   ```bash
   flutter run --release
   # More realistic performance numbers
   ```

3. **Optional optimization**
   ```bash
   # If FPS < 60 or model is >20 MB:
   # - Decimate mesh in Blender
   # - Reduce texture sizes
   # - Remove unused materials
   ```

4. **Fine-tune animation**
   - Adjust breathing amplitude
   - Adjust blink frequency
   - Test different viseme interpolation

---

## Support

If you get stuck:
1. Check console for error messages: `flutter run`
2. Verify file exists: `ls flutter_app/assets/models/demi.vrm`
3. Try GLB conversion: `python scripts/vrm_to_glb.py avatar.vrm output.glb`
4. Check blend shapes: `python scripts/vrm_to_glb.py avatar.vrm --check-shapes`
5. Review blend shape mappings in `avatar_display_3d.dart`

---

## File Checklist

```
✓ your_avatar.vrm                                 (original)
✓ flutter_app/assets/models/demi.vrm             (copied)
✓ flutter_app/assets/models/demi.glb             (optional, converted)
✓ flutter_app/pubspec.yaml                       (assets updated)
✓ flutter_app/lib/widgets/avatar_display_3d.dart (blend shapes updated if needed)
✓ scripts/vrm_to_glb.py                          (conversion tool)
```

You're all set! Run `flutter run` and enjoy your animated avatar! 🎉
