: Standalone loadbalancer
: ====PORTS====
: Frontend      7677 
: Loadbalancer  7676
: Backend       7675

start "OVMFC - Loadbalancer" cmd /k "python ./src/loadbalancer/server.py" > NUL
