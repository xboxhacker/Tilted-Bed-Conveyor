#!/usr/bin/env python3
"""
orca_to_belt - GCode converter for tilted bed conveyor belt 3D printers
Converts standard GCode to belt printer format with coordinate transformations
v9
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
        self.x_original = 0.0
        self.y_original = 0.0
        self.y_offset = 0.0
        self.current_offset = 0.0
        self.moveforward = 0.0
        self.z_speed = 0.0

    def calculate_transforms(self):
        """Calculate hypoteneuse and adjacent based on angle"""
        self.hyp = 1 / math.cos((90 - self.angle) / 180 * math.pi)
        self.adj = math.tan((90 - self.angle) / 180 * math.pi)

    def detect_slicer(self, filepath):
        """Detect which slicer generated the GCode"""
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

    def is_blank_g1(self, line):
        """Check if a G1 command has no X, Y, Z, or E parameters"""
        line = line.strip()
        if not (line.startswith("G1") or line.startswith("G0")):
            return False
        
        # Remove the G1/G0 command and any comments
        parts = line.split(';')[0].strip().split()
        if len(parts) <= 1:
            # Only "G1" or "G0" with nothing else
            return True
        
        # Check if any of the parts are X, Y, Z, or E movements
        has_movement = False
        for part in parts[1:]:  # Skip the G1/G0 itself
            if part.startswith(('X', 'Y', 'Z', 'E')):
                has_movement = True
                break
        
        return not has_movement

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
                        temp[i] = f"Y{calculated_y:.4f}"  # Limit Y to 4 decimal places
                        y_processed = True
                    except ValueError:
                        pass

                elif segment.startswith("Z") and not z_processed:
                    try:
                        current_z = float(segment[1:])
                        if self.current_offset == 0.0:
                            self.current_offset = current_z * self.adj
                        z_value = current_z * self.hyp
                        temp[i] = f"Z{z_value:.4f}"  # Limit Z to 4 decimal places
                        z_index = i
                        self.y_offset = current_z * self.adj - self.current_offset
                        z_processed = True
                    except ValueError:
                        pass

                elif segment.startswith("E") and not e_processed:
                    # Preserve E value as is
                    e_processed = True

                elif segment.startswith("F") and not f_processed:
                    # Preserve F value as is
                    f_processed = True

            # If z_speed is set and we found a Z value, split the line
            if self.z_speed > 0 and z_processed and z_value is not None:
                # Remove Z from the current line
                temp.pop(z_index)
                xy_line = ' '.join(temp)
                # Put Z movement BEFORE the XY movement for safety
                line_data = f"G1 Z{z_value:.4f} F{self.z_speed:.0f} ;Adjusted Speed Limit\n{xy_line}"
            else:
                line_data = ' '.join(temp)

        return line_data

    def process_file(self, input_file, x_offset=0.0, y_offset=0.0, angle=45.0, z_speed=0.0):
        """Process the GCode file - reads from input, writes back to same file"""
        # Set parameters
        self.x_original = x_offset
        self.y_original = y_offset
        self.angle = angle
        self.z_speed = z_speed

        # Calculate transforms
        self.calculate_transforms()

        # Detect slicer
        slicer = self.detect_slicer(input_file)

        # Read all lines from input file first
        try:
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                input_lines = f.readlines()
        except Exception as e:
            print(f"Error reading input file: {e}")
            return False

        # Process and write back to the same file
        blank_lines_removed = 0
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

                # Process each line
                for line in input_lines:
                    processed_line = self.process_line(line.rstrip('\n\r'))
                    
                    # Check for blank G1/G0 commands and skip them
                    if self.is_blank_g1(processed_line):
                        blank_lines_removed += 1
                        continue
                    
                    sw.write(processed_line + '\n')

        except Exception as ex:
            print(f"Error processing file: {ex}")
            return False

        print("orca_to_belt Complete")
        if self.z_speed > 0:
            print(f"Z movements limited to F{self.z_speed:.0f} (executed before XY)")
        if blank_lines_removed > 0:
            print(f"Removed {blank_lines_removed} blank G1/G0 command(s)")
        return True


def main():
    """Main entry point"""
    try:
        # Set up argument parser
        parser = argparse.ArgumentParser(
            description='orca_to_belt - GCode converter for tilted bed conveyor belt 3D printers',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  orca_to_belt.py input.gcode
  orca_to_belt.py input.gcode -x_offset 10 -y_offset 5 -angle 45.28
  orca_to_belt.py input.gcode -angle 45.28 -z_speed 300
  orca_to_belt.py "[output_filepath]" -x_offset 0 -y_offset 0 -angle 45.28 -z_speed 300
            """
        )
        
        parser.add_argument('input_file', 
                          help='Input GCode file path')
        parser.add_argument('-x_offset', 
                          type=float, 
                          default=0.0,
                          help='X axis offset in mm (default: 0.0)')
        parser.add_argument('-y_offset', 
                          type=float, 
                          default=0.0,
                          help='Y axis offset in mm (default: 0.0)')
        parser.add_argument('-angle', 
                          type=float, 
                          default=45.0,
                          help='Belt gantry angle in degrees (default: 45.0)')
        parser.add_argument('-z_speed', 
                          type=float, 
                          default=0.0,
                          help='Z axis feedrate in mm/min (default: 0 = no change). If set, Z movements are split and executed BEFORE XY movements for collision safety.')

        args = parser.parse_args()

        # Check if input file exists
        if not os.path.exists(args.input_file):
            print(f"Error: Input file '{args.input_file}' not found")
            print(f"Attempted path: {os.path.abspath(args.input_file)}")
            sys.exit(1)

        # Process the file
        converter = OrcaToBelt()
        success = converter.process_file(args.input_file, args.x_offset, args.y_offset, args.angle, args.z_speed)
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
