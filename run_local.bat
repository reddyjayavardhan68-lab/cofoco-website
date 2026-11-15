@echo off
cd /d "%~dp0"
echo ===============================================================
echo   Starting COFOCO Application Server
echo   Access at: http://127.0.0.1:8080/
echo   Owner Portal: http://127.0.0.1:8080/#/admin
echo ===============================================================
"C:\Users\mvish\AppData\Local\Programs\Python\Python313\python.exe" server.py
pause
