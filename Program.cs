using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.IO;
using System.Threading.Tasks;
using System.Globalization;

namespace GCodeShifter
{
    class Program
    {
        static double Angle = 45.0;
        static double Hyp = 0.0;
        static double Adj = 0.0;

        static double x_original = 0;
        static double y_original = 0;
        static double y_offset;
        static double currentOffset = 0.0;
        static double moveforward = 0;

        static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: GCodeShifter.exe <input_file> [x_offset] [y_offset] [angle]");
                return;
            }

            string inputFile = args[0];
            string tempFile = inputFile + "_temp.gcode";
            string Slicer = "";

            File.Delete(tempFile);
            File.Copy(inputFile, tempFile);

            if (args.Length > 1) Double.TryParse(args[1], out x_original);
            if (args.Length > 2) Double.TryParse(args[2], out y_original);
            if (args.Length > 3) Double.TryParse(args[3], out Angle);

            Hyp = 1 / Math.Cos((90 - Angle) / 180 * Math.PI);
            Adj = Math.Tan((90 - Angle) / 180 * Math.PI);

            // Detect slicer
            using (StreamReader sr = File.OpenText(tempFile))
            {
                string s;
                while ((s = sr.ReadLine()) != null && Slicer == "")
                {
                    if (s.Contains("Cura_SteamEngine")) Slicer = "Cura";
                    if (s.Contains("Simplify3D(R)")) Slicer = "S3D";
                    if (s.Contains("OrcaSlicer")) Slicer = "OrcaSlicer";
                }
            }

            // Process file and overwrite input with header injection
            try
            {
                using (StreamReader sr = File.OpenText(tempFile))
                {
                    using (StreamWriter sw = new StreamWriter(inputFile))
                    {
                        // Inject custom header lines at the start
                        sw.WriteLine("; HEADER_BLOCK_START");
                        sw.WriteLine("; Dimension: 250.000 9999.000 250.000 0.800");
                        sw.WriteLine("; Belt Printer: 1");
                        sw.WriteLine("; Belt Offset Y: 0.000");
                        sw.WriteLine("; Belt Offset Z: 3570.535");
                        sw.WriteLine("; Belt Gantry Angle: 45");

                        string s;
                        while ((s = sr.ReadLine()) != null)
                        {
                            sw.WriteLine(ProcessLine(s.TrimStart(), sw, Slicer));
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message);
            }

            File.Delete(tempFile);
            Console.WriteLine("GCodeShifter Complete");
        }

        static string ProcessLine(string lineData, StreamWriter sw, string slicer)
        {
            string[] temp = lineData.Split(' ');
            StringBuilder tempData = new StringBuilder(temp.Length);

            if (temp[0] == "G0" && lineData.IndexOf("Z") > 0 && slicer == "Cura")
            {
                double currentZ = double.Parse(lineData.Substring(lineData.IndexOf("Z") + 1, (lineData.Length - lineData.IndexOf("Z") - 1)));
                if (currentOffset == 0.0)
                {
                    currentOffset = currentZ * Adj;
                }
                lineData = lineData.Substring(0, lineData.IndexOf("Z") + 1) + (currentZ * Hyp).ToString();
                temp = lineData.Split(' ');
                y_offset = currentZ * Adj - currentOffset;
            }

            if (temp[0] == "G1" && lineData.IndexOf("Z") > 0 && slicer == "OrcaSlicer")
            {
                int zIndex = lineData.IndexOf("Z") + 1;
                string zPart = lineData.Substring(zIndex).Trim();
                string[] parts = zPart.Split(' ');
                string zValueStr = parts[0];

                double currentZ;
                if (double.TryParse(zValueStr, out currentZ))
                {
                    if (currentOffset == 0.0)
                    {
                        currentOffset = currentZ * Adj;
                    }
                    lineData = lineData.Substring(0, lineData.IndexOf("Z") + 1) + (currentZ * Hyp).ToString();
                    temp = lineData.Split(' ');
                    y_offset = currentZ * Adj - currentOffset;
                }
                else
                {
                    Console.WriteLine("Failed to parse Z value: " + zValueStr);
                }
            }

            if (currentOffset != 0.0)
            {
                if (temp[0] == "G0" || temp[0] == "G1")
                {
                    if (lineData.IndexOf("X") > 0 && lineData.IndexOf("Y") > 0)
                    {
                        bool xFixed = false;
                        bool yFixed = false;

                        for (int segment = 0; segment < temp.Length; segment++)
                        {
                            if (temp[segment].StartsWith("X") && !xFixed)
                            {
                                double xValue = double.Parse(temp[segment].Substring(1));
                                temp[segment] = "X" + (xValue + x_original).ToString();
                                xFixed = true;
                            }

                            if (temp[segment].StartsWith("Y") && !yFixed)
                            {
                                if (moveforward == 0) { moveforward = double.Parse(temp[segment].Substring(1)); }
                                double yValue = double.Parse(temp[segment].Substring(1));
                                temp[segment] = "Y" + (yValue + y_offset + y_original - moveforward).ToString();
                                yFixed = true;
                            }
                        }

                        lineData = string.Join(" ", temp);
                    }
                }
            }
            return lineData;
        }
    }
}
