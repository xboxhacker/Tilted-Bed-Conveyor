# Orca_to_Belt
OrcaSlicer post script to convert to belt printing.
Based on the work of zechyc.

**THIS IS A WORK IN PROGRESS**
This script only works with Orca Slicer and Windows.

# Usage

Add a generic printer to Orca to start a profile for your belt printer. Adjust the build plate Y and Z to about 600-1000. **DO NOT make it 99999**. You will have issues zooming in and panning around. You want to make it the size of your object.

Still working on a purge line, so for now, remove it from the start GCODE section in Orca. This is mine:
```
M190 S[bed_temperature_initial_layer_single]
M109 S[nozzle_temperature_initial_layer]
PRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]
G28           ;Home
G92 E0        ; Set axis to 0
G1 E25        ;Blob Purge
;G1 Z-0.4     ;USE THIS FOR A BELT OFFSET! A negative number will make more space between the nozzle and bed.
FMS_on
G92 E0 Z0

```

### NOTE: Supports are not going to work with this script unless you build them into your file.


# If you are getting a `Move out of range:` error:

Change this in your `printer.cfg`
```
[stepper_y]
position_min: -6.0
```
This will allow for a lower Y movement on the belt. Make sure you do not crash the nozzle! Keep an eye on it.

---
Download the `orca_to_belt.exe` file to your computer.

https://github.com/xboxhacker/Tilted-Bed-Conveyor/releases/

This program is not Mac or Linux compatible. Sorry.


In OrcaSlicer>Others, add this to the postprocessing script section:
`"full\path\to\orca_to_belt.exe" [x_offset] [y_offset] [angle]`
Change your path to the file. Offsets are optional and not needed.

![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/postporcessing.png)

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

 # Tesing Volumetric Flow in Orca
I have created a STEP file for testing flow. It can be found here: https://www.printables.com/model/1228148
You need to replace the `SpeedTestStructure.step` in the orca folder. Make sure to make a backup!

The model has 5mm graduated marks to help find your max flow.

 ![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/volumetric1.png)

![alt text](https://github.com/xboxhacker/Tilted-Bed-Conveyor/blob/master/images/volumetric2.png)

 

