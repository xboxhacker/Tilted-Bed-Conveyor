# Orca_to_Belt
OrcaSlicer post script to convert to belt printing.
Based on the work of zechyc.

**THIS IS A WORK IN PROGRESS; IT HAS SOME BUGS**

# Usage

Add a generic printer to Orca to start a profile for your belt printer. Adjust the build plate Y and Z to about 600-1000. **DO NOT make it 99999**. You will have issues zooming in and panning around. You want to make it the size of your object.

Still working on a purge line, so for now, remove it from the start GCODE section in Orca. This is mine:
```
M190 S[bed_temperature_initial_layer_single]
M109 S[nozzle_temperature_initial_layer]
PRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]
G92 E0        ; Set axis to 0
;G1 Z20 E25 F800
G1 E25
FMS_on
;G1 X250 E50 F2000
G92 Z0
G92 E0 Z0

```

### NOTE: Supports are not going to work with this script unless you build them into your file.

---
Download the `orca_to_belt.exe` file to your computer.

https://github.com/xboxhacker/Tilted-Bed-Conveyor/releases/

This program is not Mac or Linux compatible. Sorry.


In OrcaSlicer>Others, add this to the postprocessing script section:
`"full\path\to\orca_to_belt.exe" [x_offset] [y_offset] [angle]`
Change your path to the file. Offsets are optional and not needed.

![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/postporcessing.png)

---

 Add your object to the build plate. Rotate the object 45 degrees on the X axis (RED). Make sure your `First Layer Height` and `Layer Height` are the same, or Orca will throw an error.
 
 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/rotate45d.png)

---

 Slice your file and save your GCODE to the hard drive.
 Drag the saved GCODE back to Orca to see the preview. It should look like this.

### NOTE: The preview will be mirrored!!
 
 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/preview.png)

 ---

 
# Cube printed on IR3V2, sliced with Orca!
 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/20250311_121605.jpg)
 

