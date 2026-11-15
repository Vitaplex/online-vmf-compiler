# Online VMF compiler 

<div style="width:128px;">

![logo](/src/frontend/static/media/logo.png)  
</div>

Gimmicky application for offloading Source engine map compiling tasks to a remote server.  
* Parses the .vmf file
* Resolves user-submitted custom assets using **webkitdirectory**.  
  * **User submitted files are uploaded and persisted to the server.**
* No login
* Compile multiple files at the same time
* **Job-management**: see compile job's status (status and compile logs in real-time)
  * Download compiled .BSP (permalink)

## Cluster setup (Loadbalancer)
The Loadbalancer webservice (`/src/loadbalancer`) can be configured to point towards several systems (**Nodes**) running the Backend webservice (`/src/backend`). The loadbalancer will query each node and send the compile request to whatever node has the lowest current load.

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart
lb["LoadBalancer"]

Client --> lb
lb --> s1["System 1"]
lb --> s2["System 2"]
lb --> s3["System 3"]
lb --> s5@{ shape: procs, label: "Other systems"}
```

### Configurating multiple Nodes
Edit `/src/loabalancer/nodes.json` to set up the Nodes that should be used. A `weight`-parameter can be used to give certain Nodes higher or lower priority, if they have different specifications.
#### Example Node
```json
{
    "name": "Middleton",
    "address": "http://192.168.0.74",
    "weight": 5
}
```

## Future features
* [x] Load-balancer middleware to spread compiler tasks across multiple computers (cluster setup)?
* [ ] Packing custom assets automatically?