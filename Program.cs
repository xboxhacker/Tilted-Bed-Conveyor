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

            // Handle G0/G1 lines
            if (temp[0] == "G0" || temp[0] == "G1")
            {
                bool xProcessed = false;
                bool yProcessed = false;
                bool zProcessed = false;
                bool eProcessed = false;
                bool fProcessed = false;

                for (int segment = 0; segment < temp.Length; segment++)
                {
                    if (temp[segment].StartsWith("X") && !xProcessed)
                    {
                        double xValue = double.Parse(temp[segment].Substring(1));
                        temp[segment] = "X" + (xValue + x_original).ToString();
                        xProcessed = true;
                    }
                    else if (temp[segment].StartsWith("Y") && !yProcessed)
                    {
                        double yValue = double.Parse(temp[segment].Substring(1));
                        if (moveforward == 0) { moveforward = yValue; }
                        temp[segment] = "Y" + (yValue + y_offset + y_original - moveforward).ToString();
                        yProcessed = true;
                    }
                    else if (temp[segment].StartsWith("Z") && !zProcessed)
                    {
                        double currentZ = double.Parse(temp[segment].Substring(1));
                        if (currentOffset == 0.0)
                        {
                            currentOffset = currentZ * Adj;
                        }
                        temp[segment] = "Z" + (currentZ * Hyp).ToString("F4"); // Limit Z to 4 decimal places
                        y_offset = currentZ * Adj - currentOffset;
                        zProcessed = true;
                    }
                    else if (temp[segment].StartsWith("E") && !eProcessed)
                    {
                        // Preserve E value as is
                        eProcessed = true;
                    }
                    else if (temp[segment].StartsWith("F") && !fProcessed)
                    {
                        // Preserve F value as is
                        fProcessed = true;
                    }
                }

                lineData = string.Join(" ", temp);
            }

            return lineData;
        }
    }
}
