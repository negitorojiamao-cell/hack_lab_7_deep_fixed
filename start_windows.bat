@echo off
setlocal
rem Start in a persistent command window, so errors never make the window vanish.
if /I not "%~1"=="--run" (
    start "HACK-LAB Server" "%ComSpec%" /k ""%~f0" --run"
    exit /b
)

cd /d "%~dp0"
if errorlevel 1 goto :bad_folder
 title HACK-LAB 7.0 DEEP - Server
cls
echo ============================================================
echo HACK-LAB 7.0 DEEP - Windows launcher
echo ============================================================
echo.
echo Folder: %CD%
echo This window must remain open while you use HACK-LAB.
echo.

if not exist "server.py" goto :missing_server
if not exist "index.html" goto :missing_index

rem Pick a working Python interpreter. This project needs Python 3.10+.
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python --version >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)
if not defined PYTHON_CMD goto :no_python

%PYTHON_CMD% --version
echo.

rem Create .env from the template on first launch, without overwriting an existing one.
if not exist ".env" if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    if errorlevel 1 echo WARNING: Could not create .env automatically.
)
if not exist ".env" (
    echo WARNING: .env was not found. The site may open, but Gemini tutor will not work.
) else (
    findstr /b /c:"GEMINI_API_KEY=" ".env" >nul 2>nul
    if errorlevel 1 echo WARNING: Add GEMINI_API_KEY=... to the .env file to enable Gemini.
)

echo Starting local web server...
echo Open this address in your browser: http://127.0.0.1:8765/
echo Press Ctrl+C to stop the server.
echo.
%PYTHON_CMD% server.py
set "SERVER_EXIT=%ERRORLEVEL%"
echo.
if not "%SERVER_EXIT%"=="0" (
    echo HACK-LAB stopped with error code %SERVER_EXIT%.
    echo Read the error message above. Common causes: Python setup, invalid .env, or port 8765 already in use.
) else (
    echo HACK-LAB server has stopped.
)
echo.
echo This window will stay open so you can read the message.
pause
exit /b %SERVER_EXIT%

:no_python
echo ERROR: Python 3 was not found.
echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
echo During setup, enable the option to add Python to PATH, then reopen this launcher.
echo.
pause
exit /b 1

:missing_server
echo ERROR: server.py is missing from this folder.
echo Please extract the entire ZIP again and run start_windows.bat from the extracted folder.
echo.
pause
exit /b 1

:missing_index
echo ERROR: index.html is missing from this folder.
echo Please extract the entire ZIP again and run start_windows.bat from the extracted folder.
echo.
pause
exit /b 1

:bad_folder
echo ERROR: Could not switch to the application folder.
echo Move the complete extracted folder to a normal local folder such as Desktop, then retry.
echo.
pause
exit /b 1
