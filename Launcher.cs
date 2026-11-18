using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

namespace QWorkMateLauncher
{
    class Program
    {
        static string adbPath = @"C:\Users\w2005\AppData\Local\AppLab\a15\data\packages\arduino\tools\adb\32.0.0\adb.exe";
        static string projectDir = @"f:\Antigravity\AIoT_midterm_project";

        static void Main(string[] args)
        {
            Console.Title = "🐾 Q-WorkMate / LumiPet 專案啟動器";
            try { Console.OutputEncoding = System.Text.Encoding.UTF8; } catch {}

            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("==================================================================");
            Console.WriteLine("      🐾 Q-WorkMate - Arduino UNO Q AI 桌面生產力桌寵");
            Console.WriteLine("==================================================================");
            Console.ResetColor();
            Console.WriteLine();

            // 1. Check ADB
            if (!File.Exists(adbPath))
            {
                adbPath = "adb.exe";
            }

            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("[1/4] 檢查 Arduino UNO Q 連線狀態...");
            Console.ResetColor();

            string adbState = RunCommand(adbPath, "get-state").Trim();
            if (!adbState.Contains("device"))
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("⚠️ 尚未檢測到 Arduino UNO Q 板子，請確認 USB 傳輸線已妥善連接！");
                Console.ResetColor();
                Console.WriteLine("請接妥板子後，按任意鍵繼續檢查...");
                Console.ReadKey();
            }
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("✓ Arduino UNO Q 已連線！\n");
            Console.ResetColor();

            // 2. Start Board Docker containers (smile-matrix bridge + qpet agent)
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("[2/4] 啟動板端點陣硬體橋接與 Q-Pet Agent (Docker)...");
            Console.ResetColor();

            string startRes = RunCommand(adbPath, "shell \"docker start smile-matrix-main-1 qpet 2>&1\"");
            if (startRes.Contains("No such container") || startRes.Contains("Error"))
            {
                Console.WriteLine("板端點陣韌體準備中，正在載入點陣驅動 (初次開機需約 10 秒)...");
                RunCommand(adbPath, "shell \"arduino-app-cli app start user:smile-matrix && docker start qpet\"");
            }

            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("✓ 板端硬體與 Q-Pet 服務已啟動運行！\n");
            Console.ResetColor();

            // 3. Start proxy
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("[3/4] 啟動 Windows 本機轉發代理 (Port 7790)...");
            Console.ResetColor();
            StartProxy();
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("✓ 連線轉發代理就緒 (http://localhost:7790)！\n");
            Console.ResetColor();

            // 4. Open Browser
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("[4/4] 開啟 Web 互動儀表板...");
            Console.ResetColor();
            Thread.Sleep(1500);
            try
            {
                Process.Start("http://localhost:7790");
            }
            catch {}
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("✓ 瀏覽器已開啟！\n");
            Console.ResetColor();

            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("==================================================================");
            Console.WriteLine("  ✨ Q-WorkMate 運作中！");
            Console.WriteLine("  - 儀表板網址: http://localhost:7790");
            Console.WriteLine("  - 若要結束並停止服務，請按 [Q] 鍵或 [Enter] 鍵。");
            Console.WriteLine("==================================================================");
            Console.ResetColor();

            AppDomain.CurrentDomain.ProcessExit += (s, e) => Shutdown();

            while (true)
            {
                var key = Console.ReadKey(true);
                if (key.Key == ConsoleKey.Q || key.Key == ConsoleKey.Enter || key.Key == ConsoleKey.Escape)
                {
                    break;
                }
            }

            Shutdown();
        }

        static void StartProxy()
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = "python.exe";
                psi.Arguments = Path.Combine(projectDir, "proxy_7790.py");
                psi.WindowStyle = ProcessWindowStyle.Hidden;
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                Console.WriteLine("代理啟動提醒: " + ex.Message);
            }
        }

        static void Shutdown()
        {
            Console.WriteLine();
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("🛑 正在停止 Q-WorkMate 並熄滅點陣硬體...");
            Console.ResetColor();

            // Turn off LED matrix
            RunCommand(adbPath, "shell \"docker exec qpet python3 -c \\\"from pet_matrix import PetMatrix; m = PetMatrix(); m.draw_raw([0]*104); m.stop()\\\"\"");

            // Stop container
            RunCommand(adbPath, "shell \"docker stop qpet smile-matrix-main-1\"");

            // Kill proxy via PowerShell
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo("powershell", "-Command \"Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*proxy_7790.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }\"");
                psi.WindowStyle = ProcessWindowStyle.Hidden;
                psi.CreateNoWindow = true;
                var p = Process.Start(psi);
                if (p != null) p.WaitForExit(3000);
            }
            catch {}

            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("✓ 點陣螢幕已熄滅，所有服務已完全停止。");
            Console.ResetColor();
            Thread.Sleep(800);
        }

        static string RunCommand(string file, string args)
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = file;
                psi.Arguments = args;
                psi.RedirectStandardOutput = true;
                psi.RedirectStandardError = true;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                using (Process p = Process.Start(psi))
                {
                    string output = p.StandardOutput.ReadToEnd();
                    p.WaitForExit(8000);
                    return output;
                }
            }
            catch (Exception e)
            {
                return e.Message;
            }
        }
    }
}
