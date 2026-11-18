@echo off
chcp 65001 >nul
title 🛑 停止 Q-WorkMate 服務
cls

echo ================================================================
echo    🛑 正在停止 Q-WorkMate 服務並關閉硬體...
echo ================================================================
echo.

set ADB="C:\Users\w2005\AppData\Local\AppLab\a15\data\packages\arduino\tools\adb\32.0.0\adb.exe"

echo [1/3] 清空並熄滅板載 8x13 LED 矩陣...
%ADB% shell "docker exec qpet python3 -c \"from pet_matrix import PetMatrix; m = PetMatrix(); m.draw_raw([0]*104); m.stop()\"" >nul 2>&1

echo [2/3] 停止板端 Docker 容器...
%ADB% shell "docker stop qpet smile-matrix-main-1" >nul 2>&1
echo [V] 板端容器已停止！

echo [3/3] 終止 Windows 連線轉發代理...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*proxy_7790.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
echo [V] Windows 代理已關閉！

echo.
echo ================================================================
echo    ✨ Q-WorkMate 所有服務已全數停止，點陣螢幕已熄滅！
echo ================================================================
echo.
ping 127.0.0.1 -n 3 >nul
