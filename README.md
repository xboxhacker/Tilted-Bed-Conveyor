# Orca_to_Belt
OrcaSlicer post-processing script to convert standard GCode to belt printer format.
Based on the work of [zechyc](https://github.com/zechyc/Tilted-Bed-Conveyor)

**Cross-Platform Python Script** - Works on Windows, macOS, and Linux!

# Features

✅ **Coordinate transformation** for tilted bed geometry  
✅ **Named parameters** for easy configuration  
✅ **Z-speed control** - Independent feedrate for Z movements (executed before XY for safety)  
✅ **Layer compensation** - Fine-tune layer height with percentage adjustment  
✅ **Automatic header injection** for belt printer compatibility  
✅ **Cross-platform** - Python 3.6+ required  

# Usage

Add a generic printer to Orca to start a profile for your belt printer. Adjust the build plate Y and Z to about 600-1000. **DO NOT make it 99999**. You will have issues zooming in and panning around.

Still working on a purge line, so for now, remove it from the start GCODE section in Orca. This is mine:
```gcode
M190 S[bed_temperature_initial_layer_single]
M109 S[nozzle_temperature_initial_layer]
PRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]
BED_MESH_PROFILE LOAD=default ; IMPORTANT!!
G28           ;Home
G92 E0        ; Set axis to 0
G1 E25        ;Blob Purge
;G1 Z-0.4     ;USE THIS FOR A BELT OFFSET! A negative number will make more space between the nozzle and bed.
FMS_on
G92 E0 Z0

```

### NOTE: Supports are not going to work with this script unless you build them into your STL file.


### If you are getting a `Move out of range:` error -

Change this in your `printer.cfg`
```ini
[stepper_y]
position_min: -6.0
```
This will allow for a lower Y movement on the belt. Make sure you do not crash the nozzle! Keep an eye on it.

---

## Installation

### Requirements
- Python 3.6 or higher

### Download the Script

Download `orca_to_belt.py` from the releases page:

https://github.com/xboxhacker/Tilted-Bed-Conveyor/releases/

Or clone the repository:
```bash
git clone https://github.com/xboxhacker/Tilted-Bed-Conveyor.git
```

---

## OrcaSlicer Configuration

In **OrcaSlicer → Printer Settings → Post-processing scripts**, add:

### Windows:
```batch
"C:\Users\YourUsername\AppData\Local\Programs\Python\Python312\python.exe" "C:\Path\To\orca_to_belt.py" "[output_filepath]" -x_offset 0 -y_offset 0 -angle 45.28 -z_speed 300 -layer_comp 0.663
```

### macOS/Linux:
```bash
python3 /path/to/orca_to_belt.py "[output_filepath]" -x_offset 0 -y_offset 0 -angle 45.28 -z_speed 300 -layer_comp 0.663
```

![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/postporcessing.png)

### Parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `input_file` | GCode file path (use `[output_filepath]` in OrcaSlicer) | Required |
| `-x_offset` | X axis offset in mm | 0.0 |
| `-y_offset` | Y axis offset in mm | 0.0 |
| `-angle` | Belt gantry angle in degrees | 45.0 |
| `-z_speed` | Z axis feedrate in mm/min (0 = no change) | 0.0 |
| `-layer_comp` | Layer height compensation as percentage | 0.0 |

### Examples:

**Basic (defaults):**
```bash
python3 orca_to_belt.py input.gcode
```

**With custom angle:**
```bash
python3 orca_to_belt.py input.gcode -angle 45.28
```

**With Z speed control (recommended):**
```bash
python3 orca_to_belt.py input.gcode -angle 45.28 -z_speed 300
```

**With layer compensation:**
```bash
python3 orca_to_belt.py input.gcode -angle 45.28 -z_speed 300 -layer_comp 0.663
```

**All parameters:**
```bash
python3 orca_to_belt.py input.gcode -x_offset 0 -y_offset 0 -angle 45.28 -z_speed 300 -layer_comp 0.663
```

### Z-Speed Control

The `-z_speed` parameter allows you to control Z movement speed independently from XY movements. This is useful when OrcaSlicer's rapid moves (F21000) are too fast for your belt printer's Z axis.

When `-z_speed` is set to a positive value:
- Z movements are separated from XY movements
- Z moves **BEFORE** XY for collision safety
- Z uses the specified feedrate instead of the line's F value

**Example transformation with `-z_speed 300`:**

**Before:**
```gcode
G1 X202.873 Y472.886 Z1.2 F21000
```

**After:**
```gcode
G1 Z1.2 F300 ;Adjusted Speed Limit
G1 X202.873 Y472.8863 F21000
```

### Layer Compensation

The `-layer_comp` parameter allows fine-tuning of the transformed layer height using a percentage adjustment. This is useful for compensating flow characteristics specific to belt printing.

**How it works:**

When you slice with a layer height (e.g., 0.6 mm), the script transforms it based on your belt angle:
```
Transformed Z = Original Z × (1 / cos(90° - angle))
```

With `-layer_comp`, you can adjust this further:
```
Final Z = Transformed Z × (1 + layer_comp / 100)
```

**Example with 0.6 mm layer height and 45.28° angle:**

| Without Compensation | With `-layer_comp 0.663` |
|---------------------|-------------------------|
| 0.6 × 1.4074 = 0.8444 mm | 0.8444 × 1.00663 = 0.8500 mm |

**Use cases:**
- **Positive values** (+0.5 to +2%): Increase layer height for better adhesion or faster prints
- **Negative values** (-0.5 to -2%): Decrease layer height for finer detail or better surface finish
- **Zero (default)**: No compensation, use calculated transformation only

---

 Add your object to the build plate. Rotate the object 45 degrees on the X axis (RED). Make sure your `First Layer Height` and `Layer Height` are the same (or very close), or Orca will throw an error.

### NOTE: The face noted in the image will be printed flat on the belt.
 
 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/face.png)

---

 Slice your file and save your GCODE to the hard drive.
 Drag the saved GCODE back to Orca to see the preview. It should look like this.

 
 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/xyz1.jpg)
 

 You can drop it into Ideamaker and get a "normal" preview.
 
![alt_text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/xyz2.jpg)



 ---

 
# Cube printed on IR3V2, sliced with Orca!

 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/20250311_121605.jpg)


 ---

 # Testing Volumetric Flow in Orca
I have created a STEP file for testing flow. It can be found here: https://www.printables.com/model/1228148
You need to replace the `SpeedTestStructure.step` in the orca folder. Make sure to make a backup!

The model has 5mm graduated marks to help find your max flow.

 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/volumetric1.png)

![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/volumetric2.png)

 

---

## Command-Line Usage

You can also run the script directly from the command line:

```bash
python3 orca_to_belt.py --help
```

Output:
```
usage: orca_to_belt.py [-h] [-x_offset X_OFFSET] [-y_offset Y_OFFSET] 
                       [-angle ANGLE] [-z_speed Z_SPEED] [-layer_comp LAYER_COMP] input_file

orca_to_belt - GCode converter for tilted bed conveyor belt 3D printers

positional arguments:
  input_file            Input GCode file path

optional arguments:
  -h, --help            show this help message and exit
  -x_offset X_OFFSET    X axis offset in mm (default: 0.0)
  -y_offset Y_OFFSET    Y axis offset in mm (default: 0.0)
  -angle ANGLE          Belt gantry angle in degrees (default: 45.0)
  -z_speed Z_SPEED      Z axis feedrate in mm/min (default: 0 = no change)
  -layer_comp LAYER_COMP
                        Layer compensation as percentage (default: 0.0)
```

---

## Troubleshooting

### Script fails with "Error code: 1"
- Make sure Python 3.6+ is installed: `python --version` or `python3 --version`
- Check that the file path to `orca_to_belt.py` is correct
- Try running the script manually first to see detailed error messages

### Z movements still too fast
- Increase the `-z_speed` value (try 100-500 mm/min)
- Check your printer's max Z velocity in `printer.cfg`

### Preview looks wrong in OrcaSlicer
- This is normal! Drag the saved GCode back into Orca or use Ideamaker for preview
- The transformed coordinates are correct for belt printing

### Layer adhesion issues
- Try adjusting `-layer_comp` by small increments (±0.5% to ±2%)
- Positive values increase layer height (better adhesion, rougher surface)
- Negative values decrease layer height (finer detail, may reduce adhesion)

---

## Credits

Based on the original work of [zechyc](https://github.com/zechyc/Tilted-Bed-Conveyor)

Python conversion and enhancements by [xboxhacker](https://github.com/xboxhacker)

**Script Version:** v13  
**Last Updated:** October 2025
