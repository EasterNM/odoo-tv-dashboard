@echo off
setlocal

title Refresh M-TECH Dashboard DNS

echo [1/2] Clearing the Windows DNS cache...
ipconfig /flushdns
if errorlevel 1 (
    echo.
    echo ERROR: DNS cache could not be cleared.
    echo Right-click this file and select "Run as administrator", then try again.
    pause
    exit /b 1
)

echo.
echo [2/2] Checking the dashboard hostname...
nslookup mtech.tail3a0947.ts.net

echo.
echo DNS cache refresh completed.
echo Close all browser windows, reopen the browser, and visit:
echo https://mtech.tail3a0947.ts.net:8443/store
echo.
echo If the link still fails, use the internal company-network URL:
echo http://10.2.3.23:8000/store
echo.
pause
exit /b 0
