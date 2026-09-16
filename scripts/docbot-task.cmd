@echo off
rem Launcher for the Windows scheduled task "docbot". Runs the supervisor from the repo root
rem so .env, bin\cloudflared.exe and state\ resolve. Supervisor restarts its children itself;
rem the task's own restart policy covers the supervisor.
cd /d "%~dp0.."
"C:\Users\Josh\AppData\Local\Programs\Python\Python313\python.exe" -m worker supervise >> state\supervisor.log 2>&1
