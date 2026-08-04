@echo off
rem Registered by `scripts\dev.ps1 -AutoStart` as a logon scheduled task.
rem Starts AUREON (server + self-healing watchdog) in the background,
rem then exits so the task returns immediately.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" -Watch
