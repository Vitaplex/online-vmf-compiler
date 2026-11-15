: Standalone backend
: ====PORTS====
: Frontend      7677 
: Loadbalancer  7676
: Backend       7675

start "OVMFC - Server" cmd /k "python ./src/backend/server.py" > NUL
