#!/usr/bin/env python3
"""
orca_to_belt - GCode converter for tilted bed conveyor belt 3D printers
Converts standard GCode to belt printer format with coordinate transformations.
"""

__version__ = "1.19.0"  # Incremented - force negative Y values to 0.00

import sys
import os
import math
import argparse
import json
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:  # Tk may be unavailable on some systems
    tk = None
    messagebox = None


CONFIG_FILENAME = "orca_to_belt_config.json"
DEFAULT_OPTIONS = {
    "x_offset": 0.0,
    "y_offset": 0.0,
    "angle": 45.0,
    "z_speed": 0.0,
    "layer_comp": 0.0,
    "add_m400": False,
}


def get_config_path(custom_path=None):
    """Return path to config file, falling back to script directory."""
    if custom_path:
        return Path(custom_path)
    return Path(__file__).with_name(CONFIG_FILENAME)


def load_config(path):
    """Load persisted options, falling back to defaults on failure."""
    if path is None or not path.exists():
        return DEFAULT_OPTIONS.copy()
    try:
        with open(path, 'r', encoding='utf-8') as cfg:
            data = json.load(cfg)
        merged = DEFAULT_OPTIONS.copy()
        merged.update({k: data.get(k, v) for k, v in DEFAULT_OPTIONS.items()})
        return merged
    except Exception as exc:
        print(f"Warning: Could not read config '{path}': {exc}")
        return DEFAULT_OPTIONS.copy()


def save_config(path, data):
    """Persist option values to disk."""
    if path is None:
        return
    try:
        with open(path, 'w', encoding='utf-8') as cfg:
            json.dump(data, cfg, indent=2)
    except Exception as exc:
        print(f"Warning: Could not save config '{path}': {exc}")


def require_gui():
    """Ensure Tk is available before trying to render the GUI."""
    if tk is None:
        raise RuntimeError("Tkinter is not available on this system. Use --no-gui to run headless.")


def launch_gui(option_values, input_file, config_path):
    """Render GUI form for adjusting converter options."""
    require_gui()

    root = tk.Tk()
    root.title("orca_to_belt - Post Processing Options")

    label = tk.Label(
        root,
        text=(
            "Adjust converter options. Current selections are saved to\n"
            f"{config_path if config_path else 'config file'} when you run.\n"
            f"Target file: {os.path.basename(input_file)}"
        ),
        justify="left",
        padx=10,
        pady=10,
    )
    label.pack(anchor="w")

    form_frame = tk.Frame(root, padx=10, pady=5)
    form_frame.pack(fill="both", expand=True)

    entry_vars = {}
    fields = [
        ("X Offset (mm)", "x_offset"),
        ("Y Offset (mm)", "y_offset"),
        ("Gantry Angle (deg)", "angle"),
        ("Z Speed Limit (mm/min)", "z_speed"),
        ("Layer Compensation (%)", "layer_comp"),
    ]

    for idx, (label_text, key) in enumerate(fields):
        tk.Label(form_frame, text=label_text, anchor="w").grid(row=idx, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(option_values.get(key, DEFAULT_OPTIONS[key])))
        entry = tk.Entry(form_frame, textvariable=var, width=20)
        entry.grid(row=idx, column=1, pady=2, padx=(10, 0))
        entry_vars[key] = var

    m400_var = tk.BooleanVar(value=bool(option_values.get("add_m400", False)))
    tk.Checkbutton(form_frame, text="Insert M400 after adjusted Z moves", variable=m400_var).grid(
        row=len(fields), column=0, columnspan=2, pady=6, sticky="w"
    )

    result = {}

    def on_run():
        try:
            parsed = {
                "x_offset": float(entry_vars["x_offset"].get()),
                "y_offset": float(entry_vars["y_offset"].get()),
                "angle": float(entry_vars["angle"].get()),
                "z_speed": float(entry_vars["z_speed"].get()),
                "layer_comp": float(entry_vars["layer_comp"].get()),
                "add_m400": bool(m400_var.get()),
            }
        except ValueError as err:
            if messagebox:
                messagebox.showerror("Invalid Input", f"Please enter numeric values.\n{err}")
            else:
                print(f"Invalid input: {err}")
            return

        result.clear()
        result.update(parsed)
        root.quit()

    def on_cancel():
        result.clear()
        result["cancelled"] = True
        root.quit()

    button_frame = tk.Frame(root, pady=10)
    button_frame.pack()
    tk.Button(button_frame, text="Run Conversion", width=18, command=on_run).grid(row=0, column=0, padx=5)
    tk.Button(button_frame, text="Cancel", width=10, command=on_cancel).grid(row=0, column=1, padx=5)

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()
    root.destroy()

    if result.get("cancelled"):
        return None
    return result or None


def resolve_options(args):
    """Merge config, CLI, and GUI inputs into a final option set."""
    config_path = get_config_path(args.config_path)
    stored = load_config(config_path)

    def apply_cli_overrides(base):
        merged = base.copy()
        for key in ("x_offset", "y_offset", "angle", "z_speed", "layer_comp"):
            value = getattr(args, key, None)
            if value is not None:
                merged[key] = value
        if getattr(args, "add_m400", None) is not None:
            merged["add_m400"] = bool(args.add_m400)
        return merged

    if args.no_gui:
        final_options = apply_cli_overrides(stored)
        save_config(config_path, final_options)
        return final_options, config_path

    starting_values = apply_cli_overrides(stored)
    selections = launch_gui(starting_values, args.input_file, config_path)
    if selections is None:
        return None, config_path
    save_config(config_path, selections)
    return selections, config_path

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
        self.add_m400 = False         # Insert M400 after Z speed move
        self.last_feedrate = None     # Remember last non-Z feed rate

    def calculate_transforms(self):
        self.hyp = 1 / math.cos((90 - self.angle) / 180 * math.pi)
        self.adj = math.tan((90 - self.angle) / 180 * math.pi)

    def process_line(self, line_data):
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
            line_has_feed = False

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

                        if self.y_original != 0.0 and calculated_y < self.y_original:
                            calculated_y = self.y_original
                        
                        # Force negative Y values to 0.00
                        if calculated_y < 0.0:
                            calculated_y = 0.0

                        temp[i] = f"Y{calculated_y:.4f}"
                        y_processed = True
                    except ValueError:
                        pass

                elif segment.startswith("Z") and not z_processed:
                    try:
                        current_z = float(segment[1:])
                        if self.current_offset == 0.0:
                            self.current_offset = current_z * self.adj

                        z_transformed = current_z * self.hyp
                        z_value = z_transformed * (1.0 + self.layer_comp / 100.0)
                        temp[i] = f"Z{z_value:.4f}"
                        z_index = i

                        self.y_offset = current_z * self.adj - self.current_offset
                        z_processed = True
                    except ValueError:
                        pass

                elif segment.startswith("E") and not e_processed:
                    e_processed = True

                elif segment.startswith("F") and not f_processed:
                    try:
                        feed_value = float(segment[1:])
                        self.last_feedrate = feed_value
                        line_has_feed = True
                    except ValueError:
                        pass
                    f_processed = True

            # Z speed split and M400 logic
            if self.z_speed > 0 and z_processed and z_value is not None:
                if 0 <= z_index < len(temp):
                    temp.pop(z_index)
                # Re-apply the previous XY feed if we just forced a slow Z-only move
                needs_feed_restore = (not line_has_feed and self.last_feedrate is not None)
                xy_line = ' '.join(temp).strip()
                feed_restore_line = None

                if needs_feed_restore:
                    feed_text = f"F{self.last_feedrate:.4f}"
                    if xy_line:
                        xy_line = f"{xy_line} {feed_text}".strip()
                    else:
                        feed_restore_line = f"G1 {feed_text}".strip()

                z_line = f"G1 Z{z_value:.4f} F{self.z_speed:.0f} ;Adjusted Speed Limit"
                if self.add_m400:
                    z_line += "\nM400"
                output_lines = [z_line]
                if feed_restore_line:
                    output_lines.append(feed_restore_line)
                if xy_line:
                    output_lines.append(xy_line)
                line_data = "\n".join(filter(None, output_lines))
            else:
                line_data = ' '.join(temp)

        return line_data

    def process_file(self, input_file, x_offset=0.0, y_offset=0.0, angle=45.0, z_speed=0.0, layer_comp=0.0, add_m400=False):
        self.x_original = x_offset
        self.y_original = y_offset
        self.angle = angle
        self.z_speed = z_speed
        self.layer_comp = layer_comp
        self.add_m400 = add_m400

        self.calculate_transforms()

        try:
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                input_lines = f.readlines()
        except Exception as e:
            print(f"Error reading input file: {e}")
            return False

        try:
            with open(input_file, 'w', encoding='utf-8') as sw:
                # Custom header (always written)
                sw.write("; HEADER_BLOCK_START\n")
                sw.write("; Dimension: 250.000 9999.000 250.000 0.800\n")
                sw.write("; Belt Printer: 1\n")
                sw.write("; Belt Offset Y: 0.000\n")
                sw.write("; Belt Offset Z: 3570.535\n")
                sw.write("; Belt Gantry Angle: 45\n")
                if self.z_speed > 0:
                    sw.write(f"; Z Speed Override: {self.z_speed:.0f}\n")
                    sw.write("; Z movements execute BEFORE XY for collision safety\n")
                    if self.add_m400:
                        sw.write("; M400 inserted after Z moves for synchronization\n")
                if self.layer_comp != 0.0:
                    sw.write(f"; Layer Compensation: {self.layer_comp:+.2f}%\n")
                if self.y_original != 0.0:
                    sw.write(f"; Y Offset (anchor & minimum clamp): {self.y_original:.4f}\n")

                # Process lines only after marker
                process_mode = False
                for line in input_lines:
                    stripped_line = line.rstrip('\n\r')
                    lower_line = stripped_line.strip().lower()
                    if not process_mode:
                        sw.write(stripped_line + '\n')
                        if lower_line == "; filament start gcode" or lower_line == "; filament gcode":
                            process_mode = True
                    else:
                        processed_line = self.process_line(stripped_line)
                        sw.write(processed_line + '\n')

        except Exception as ex:
            print(f"Error processing file: {ex}")
            return False

        print("orca_to_belt Complete")
        if self.z_speed > 0:
            print(f"Z movements limited to F{self.z_speed:.0f} (executed before XY)")
            if self.add_m400:
                print("M400 inserted after Z moves for synchronization")
        if self.layer_comp != 0.0:
            print(f"Layer compensation: {self.layer_comp:+.2f}%")
        if self.y_original != 0.0:
            print(f"Y clamped to minimum of {self.y_original:.4f}")
        return True

def main():
    parser = argparse.ArgumentParser(
        description="Convert standard GCode to belt printer format with coordinate transforms."
    )
    parser.add_argument('input_file', type=str, help='Input GCode file')
    parser.add_argument('-x_offset', type=float, default=None, help='X axis offset in mm (default: stored config or 0.0)')
    parser.add_argument('-y_offset', type=float, default=None, help='Y axis offset in mm (default: stored config or 0.0)')
    parser.add_argument('-angle', type=float, default=None, help='Belt gantry angle in degrees (default: stored config or 45.0)')
    parser.add_argument('-z_speed', type=float, default=None, help='Z axis feedrate in mm/min (default: stored config or 0.0)')
    parser.add_argument('-layer_comp', type=float, default=None, help='Layer compensation as percentage (default: stored config or 0.0)')
    parser.set_defaults(add_m400=None)
    parser.add_argument('--add-m400', dest='add_m400', action='store_true', help='Force insertion of M400 after adjusted Z moves')
    parser.add_argument('--no-add-m400', dest='add_m400', action='store_false', help='Disable M400 insertion regardless of config')
    parser.add_argument('--no-gui', action='store_true', help='Skip GUI and use CLI/config values directly')
    parser.add_argument('--config-path', type=str, help='Path to config JSON (defaults next to script)')

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)

    try:
        options, _ = resolve_options(args)
    except RuntimeError as gui_error:
        print(f"Error: {gui_error}")
        sys.exit(1)

    if options is None:
        print("Conversion cancelled by user.")
        sys.exit(1)

    converter = OrcaToBelt()
    success = converter.process_file(
        args.input_file,
        options["x_offset"],
        options["y_offset"],
        options["angle"],
        options["z_speed"],
        options["layer_comp"],
        options["add_m400"],
    )
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
