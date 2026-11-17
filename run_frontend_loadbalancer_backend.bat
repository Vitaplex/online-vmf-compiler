: Client hosts the frontend, loadbalancer AND act as a cluster node (must configure self in nodes.json)
run_sa_frontend http://127.0.0.1:7676 && run_sa_loadbalancer && run_sa_backend
