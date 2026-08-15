@echo off
cd /d "%~dp0"
start "Gateway" cmd /k ".venv\Scripts\python.exe mock_gateway.py"
start "App" cmd /k ".venv\Scripts\python.exe app.py"