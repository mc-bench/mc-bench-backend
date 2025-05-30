# Minecraft Biome Tinting Technical Details

## Color Conversion Flow

This document describes how biome colors are converted from their raw format to the final applied tint.

### Overview

In Minecraft, biome-specific colors (like grass and foliage) are stored as integer values in biome data files. These values must be properly converted through several stages before being applied to textures.

## Conversion Pipeline

The color conversion process follows these steps:

1. **Raw Integer Color** → **Hex String**
   - Raw colors are stored as integer values (e.g., `1317381` for Dark Forest grass)
   - The `int_to_rgb_hex()` function converts these to hex strings (e.g., `#141A25`)

2. **Hex String** → **RGB Values**
   - The `hex_to_srgb()` function converts hex strings to RGB color values
   - This involves:
     - Parsing the hex string to RGB values (0-255 range)
     - Normalizing to 0-1 range
     - Note: We intentionally do NOT apply gamma correction to avoid darkening biome tints further

3. **Brightness Adjustment**
   - Very dark tints (brightness < 0.2) are scaled up to maintain visibility
   - Color ratios are preserved to maintain the tint's hue

4. **Application to Textures**
   - Tint is applied using the luminance-preserving method 
   - This preserves texture details while applying the biome color

## Code Implementation

### Integer to Hex Conversion

```python
def int_to_rgb_hex(color_int: int) -> str:
    """Convert an integer color value to #RGB hex format."""
    # Extract RGB components
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF

    # Format as hex string with # prefix
    return f"#{r:02X}{g:02X}{b:02X}"
```

### Hex to RGB Conversion

```python
def hex_to_srgb(hex_color: str) -> tuple[float, float, float]:
    """Convert a hex color string to RGB tuple with values between 0 and 1."""
    # Remove '#' if present
    hex_color = hex_color.lstrip("#")

    # Convert hex to RGB values (0-255)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # Normalize to 0-1 range without gamma correction
    # to avoid making colors too dark
    return (r / 255.0, g / 255.0, b / 255.0)
```

### Texture Tinting Implementation

```python
def _modify_texture_pixels(
    pixels: list[float],
    tint: Optional[tuple[float, float, float]] = None,
    contrast: float = 0.0,
) -> list[float]:
    """Modify texture pixels by applying tint and contrast adjustments."""
    modified = pixels.copy()

    # Process 4 values at a time (RGBA)
    for i in range(0, len(modified), 4):
        # Apply tint if specified
        if tint:
            # Get texture color
            r = modified[i]
            g = modified[i + 1]
            b = modified[i + 2]
            
            # Calculate luminance of the texture pixel
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            
            # Set minimum brightness for very dark tints
            min_brightness = 0.2
            tint_brightness = 0.299 * tint[0] + 0.587 * tint[1] + 0.114 * tint[2]
            
            if tint_brightness < min_brightness:
                # Scale the tint to maintain color ratios but increase brightness
                scale = min_brightness / max(0.01, tint_brightness)
                effective_tint = [
                    min(1.0, tint[0] * scale),
                    min(1.0, tint[1] * scale),
                    min(1.0, tint[2] * scale)
                ]
            else:
                effective_tint = tint
                
            # Apply tint using luminance to preserve texture detail
            modified[i] = effective_tint[0] * luminance
            modified[i + 1] = effective_tint[1] * luminance
            modified[i + 2] = effective_tint[2] * luminance
            
        # Apply contrast and ensure values stay in valid range
        # ... [additional code omitted for brevity]
```

## Example: Dark Forest Tint

For the Dark Forest biome, which has a very dark blue-gray grass color:

1. **Raw Integer**: `1317381`
2. **Hex String**: `#141A25` 
   - R: 20, G: 26, B: 37 (very dark blue-gray)
3. **Normalized RGB**: (0.078, 0.102, 0.145)
   - We skip gamma correction to preserve brightness
4. **Brightness Adjusted**: Values scaled up to meet minimum brightness if needed
5. **Applied to Texture**: Luminance-based application preserves texture detail

Previously, we were applying additional gamma correction (raising values to power of 2.2), which was making already dark colors like Dark Forest even darker. The current implementation avoids this, keeping the colors at an appropriate brightness level.

## Important Notes on Color Spaces

**Standard sRGB to Linear Workflow:**
- Typically when working with sRGB colors (as stored in image files), we convert to linear space by applying gamma correction (raising to power of 2.2) before performing operations
- After operations, we convert back to sRGB for display (raising to power of 1/2.2)

**Our Modified Approach:**
- For biome tinting, we intentionally skip the initial gamma correction step
- This prevents colors from becoming too dark, especially for biomes with already dark tint values like Dark Forest
- The luminance-based application method still produces visually appropriate results that match Minecraft's appearance

## Summary

The color conversion pipeline ensures that biome colors from the Minecraft data are correctly transformed and applied to textures in a way that maintains visual fidelity. By avoiding unnecessary gamma correction and using luminance-based tinting, we achieve the correct appearance for all biomes, including those with darker color palettes.