@echo off
rem zcc.cmd — Windows-обёртка над zcc.exe (сама сборка зовёт её из windows.mk).
rem
rem Проблема: в recipe PATH подмешивается в POSIX-стиле (".../bin:$PATH"),
rem и для нативного zcc.exe этот PATH приезжает перемешанным — zcc тогда
rem не может найти z88dk-z80asm/z88dk-appmake. Здесь кладём свой bin в
rem начало PATH в нормальном windows-виде — остальное zcc.exe делает сам.
setlocal
set "PATH=%~dp0;%PATH%"
"%~dp0zcc.exe" %*
endlocal
