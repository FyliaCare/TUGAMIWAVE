@echo off
set PYTHON_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
set PYTHON_INSTALLER=python-3.12.0-amd64.exe

echo Downloading Python 3.12.0 installer...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"

echo Download complete. Run %PYTHON_INSTALLER% to install Python 3.12.
pause