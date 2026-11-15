: Standalone frontend
: ====PORTS====
: Frontend      7677 
: Loadbalancer  7676
: Backend       7675

SET BACKEND_URL=%1
IF [%BACKEND_URL%] EQU [] SET BACKEND_URL="127.0.0.1:7675"

start "OVMFC - Client" cmd /k "python ./src/frontend/server.py" %BACKEND_URL% > NUL
