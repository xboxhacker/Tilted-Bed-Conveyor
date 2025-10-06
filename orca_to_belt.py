#!/usr/bin/env python3
"""
orca_to_belt - GCode converter for tilted bed conveyor belt 3D printers
Converts standard GCode to belt printer format with coordinate transformations
v15
"""

import sys
import os
import math
import argparse


class OrcaToBelt:
    def __init__(self):
        self.angle = 45.0
        self.hyp = 0.0
        self.adj = 0.0
        self.x_original = 0.0         # User X offset (constant)
        self.y_original = 0.0         # User Y offset (also used as clamp minimum when non-zero)
        self.y_offset = 0.0           # Dynamic Y offset from Z transform
        self.current_offset = 0.0
        self.moveforward = 0.0        # First encountered Y (for anchoring)
        self.z_speed = 0.0
        self.layer_comp = 0.0         # Percent

    def calculate_transforms(self):
        """Calculate hypotenuse and adjacent based on gantry angle"""
        self.hyp = 1 / math.cos((90 - self.angle) / 180 * math.pi)
        self.adj = math.tan((90 - self.angle) / 180 * math.pi)

    def detect_slicer(self, filepath):
        """Detect which slicer generated the GCode (best-effort)"""
        slicer = ""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "Cura_SteamEngine" in line:
                        slicer = "Cura"
                        break
                    if "Simplify3D(R)" in line:
                        slicer = "S3D"
                        break
                    if "OrcaSlicer" in line:
                        slicer = "OrcaSlicer"
                        break
        except Exception as e:
            print(f"Error detecting slicer: {e}")
        return slicer

    def process_line(self, line_data):
        """Process a single line of GCode"""
        line_data = line_data.lstrip()
        temp = line_data.split(' ')

        # Handle G0/G1 lines
        if len(temp) > 0 and (temp[0] == "G0" or temp[0] == "G1"):
            x_processed = False
            y_processed = False
            z_processed = False
            e_processed = False
            f_processed = False

            z_value = None
            z_index = -1

            for i, segment in enumerate(temp):
                if segment.startswith("X") and not x_processed:
                    try:
                        x_value = float(segment[1:])
                        temp[i] = f"X{x_value + self.x_original}"
                        x_processed = True
                    except ValueError:
                        pass

                elif segment.startswith("Y") and not y_processed:
                    try:
                        y_value = float(segment[1:])
                        if self.moveforward == 0.0:
                            self.moveforward = y_value
                        calculated_y = y_value + self.y_offset + self.y_original - self.moveforward

                        # Clamp Y to minimum y_original if y_original is non-zero
                        if self.y_original != 0.0 and calculated_y < self.y_original:
                            calculated_y = self.y_original

                        temp[i] = f"Y{calculated_y:.4f}"  # round Y to 4 decimals
                        y_processed = True
                    except ValueError:
                        pass

                elif segment.startswith("Z") and not z_processed:
                    try:
                        current_z = float(segment[1:])
                        if self.current_offset == 0.0:
                            self.current_offset = current_z * self.adj

                        # Transform Z along gantry angle
                        z_transformed = current_z * self.hyp
                        # Apply layer compensation percentage
                        z_value = z_transformed * (1.0 + self.layer_comp / 100.0)

                        temp[i] = f"Z{z_value:.4f}"  # round Z to 4 decimals
                        z_index = i

                        # Update dynamic Y offset from the Z transform
                        self.y_offset = current_z * self.adj - self.current_offset
                        z_processed = True
                    except ValueError:
                        pass

                elif segment.startswith("E") and not e_processed:
                    e_processed = True

                elif segment.startswith("F") and not f_processed:
                    f_processed = True

            # If z_speed is set and we found a Z value, split the line
            if self.z_speed > 0 and z_processed and z_value is not None:
                # Remove Z from the current line
                if 0 <= z_index < len(temp):
                    temp.pop(z_index)
                xy_line = ' '.join(temp).strip()
                # Put Z movement BEFORE the XY movement for safety
                if xy_line:
                    line_data = f"G1 Z{z_value:.4f} F{self.z_speed:.0f} ;Adjusted Speed Limit\n{xy_line}"
                else:
                    line_data = f"G1 Z{z_value:.4f} F{self.z_speed:.0f} ;Adjusted Speed Limit"
            else:
                line_data = ' '.join(temp)

        return line_data

    def process_file(self, input_file, x_offset=0.0, y_offset=0.0, angle=45.0, z_speed=0.0, layer_comp=0.0):
        """Process the GCode file - reads from input, writes back to same file"""
        # Set parameters
        self.x_original = x_offset
        self.y_original = y_offset
        self.angle = angle
        self.z_speed = z_speed
        self.layer_comp = layer_comp

        # Calculate transforms
        self.calculate_transforms()

        # Read all lines from input file first
        try:
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                input_lines = f.readlines()
        except Exception as e:
            print(f"Error reading input file: {e}")
            return False

        # Process and write back to the same file
        try:
            with open(input_file, 'w', encoding='utf-8') as sw:
                # Inject custom header lines at the start
                sw.write("; HEADER_BLOCK_START\n")
                sw.write("; Dimension: 250.000 9999.000 250.000 0.800\n")
                sw.write("; Belt Printer: 1\n")
                sw.write("; Belt Offset Y: 0.000\n")
                sw.write("; Belt Offset Z: 3570.535\n")
                sw.write("; Belt Gantry Angle: 45\n")
                if self.z_speed > 0:
                    sw.write(f"; Z Speed Override: {self.z_speed:.0f}\n")
                    sw.write("; Z movements execute BEFORE XY for collision safety\n")
                if self.layer_comp != 0.0:
                    sw.write(f"; Layer Compensation: {self.layer_comp:+.2f}%\n")
                if self.y_original != 0.0:
                    sw.write(f"; Y Offset (anchor & minimum clamp): {self.y_original:.4f}\n")

                # Process each line
                for line in input_lines:
                    processed_line = self.process_line(line.rstrip('\n\r'))
                    sw.write(processed_line + '\n')

        except Exception as ex:
            print(f"Error processing file: {ex}")
            return False

        print("orca_to_belt Complete")
        if self.z_speed > 0:
            print(f"Z movements limited to F{self.z_speed:.0f} (executed before XY)")
        if self.layer_comp != 0.0:
            print(f"Layer compensation: {self.layer_comp:+.2f}%")
        if self.y_original != 0.0:
            print(f"Y clamped to minimum of {self.y_original:.4f}")
        return True


def main():
    """Main entry point"""
    try:
        parser = argparse.ArgumentParser(
            description='orca_to_belt - GCode converter for tilted bed conveyor belt 3D printers',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  orca_to_belt.py input.gcode
  orca_to_belt.py input.gcode -x_offset 10 -y_offset 0.35 -angle 45.28
  orca_to_belt.py input.gcode -angle 45.28 -z_speed 300
  orca_to_belt.py "[output_filepath]" -x_offset 0 -y_offset 0.35 -angle 45.28 -z_speed 300 -layer_comp 0.663
            """
        )

        parser.add_argument('input_file',
                            help='Input GCode file path (OrcaSlicer passes a temp file via [output_filepath])')
        parser.add_argument('-x_offset',
                            type=float,
                            default=0.0,
                            help='X axis offset in mm (default: 0.0)')
        parser.add_argument('-y_offset',
                            type=float,
                            default=0.0,
                            help='Y axis offset in mm (default: 0.0). Also used as the minimum clamp when non-zero.')
        parser.add_argument('-angle',
                            type=float,
                            default=45.0,
                            help='Belt gantry angle in degrees (default: 45.0)')
        parser.add_argument('-z_speed',
                            type=float,
                            default=0.0,
                            help='Z axis feedrate in mm/min (default: 0 = no change). If set, Z movements are split and executed BEFORE XY movements for collision safety.')
        parser.add_argument('-layer_comp',
                            type=float,
                            default=0.0,
                            help='Layer compensation as percentage (default: 0.0). Positive increases transformed Z, negative decreases.')

        args = parser.parse_args()

        if not os.path.exists(args.input_file):
            print(f"Error: Input file '{args.input_file}' not found")
            print(f"Attempted path: {os.path.abspath(args.input_file)}")
            sys.exit(1)

        converter = OrcaToBelt()
        success = converter.process_file(
            args.input_file,
            args.x_offset,
            args.y_offset,
            args.angle,
            args.z_speed,
            args.layer_comp
        )

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
