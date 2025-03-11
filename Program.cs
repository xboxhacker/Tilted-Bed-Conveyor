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
            string inputFile = args[0];
            string tempFile = inputFile + "_temp.gcode";
            string outputFile = args[1];
            string xoffsetLength = "";
            string yoffsetLength = "";
			string newAngle = "";
            string Slicer = "";

            File.Delete(tempFile);
            File.Copy(inputFile, tempFile);

            if (args.Length > 2)
            {
                xoffsetLength = args[2];
                Double.TryParse(xoffsetLength, out x_original);
            }

            if (args.Length > 3)
            {
                yoffsetLength = args[3];
                Double.TryParse(yoffsetLength, out y_original);
            }

            if (args.Length > 4)
            {
                string newAdj = args[4];
                Double.TryParse(newAdj, out Angle);
            }

            Hyp = 1 / Math.Cos((90 - Angle) / 180 * Math.PI);
            Adj = Math.Tan((90 - Angle) / 180 * Math.PI);

            using (StreamReader sr = File.OpenText(tempFile))
            {
                using (StreamWriter sw = new StreamWriter(outputFile))
                {
                    string s = String.Empty;
                    while ((s = sr.ReadLine()) != null && Slicer == "")
                    {
                        if (s.IndexOf("Cura_SteamEngine") > 0) Slicer = "Cura";
                        if (s.IndexOf("Simplify3D(R)") > 0) Slicer = "S3D";
                        if (s.IndexOf("OrcaSlicer") > 0) Slicer = "OrcaSlicer";
                    }
                }
            }

            try
            {
                using (StreamReader sr = File.OpenText(tempFile))
                {
                    using (StreamWriter sw = new StreamWriter(outputFile))
                    {
                        string s = String.Empty;
                        while ((s = sr.ReadLine()) != null)
                        {
                            sw.WriteLine(ProcessLine(s.TrimStart(), sw, Slicer));
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message.ToString());
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
                Console.WriteLine("Cura");
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
                //Console.WriteLine("OrcaSlicer");
                //Console.WriteLine("Processing line: " + lineData);

                int zIndex = lineData.IndexOf("Z") + 1;
                string zPart = lineData.Substring(zIndex).Trim();
                string[] parts = zPart.Split(' ');
                string zValueStr = parts[0];

                //Console.WriteLine("Z value string: " + zValueStr);

                double currentZ; // Declare variable separately
                if (double.TryParse(zValueStr, out currentZ)) // Use pre-declared variable
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
