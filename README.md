# Online VMF compiler 

<div style="width:128px;">

![logo](/static/media/logo.png)  
</div>


Gimmicky application for offloading Source engine map compiling tasks to a remote server.  
* Parses the .vmf file
* Resolves user-submitted custom assets using **webkitdirectory**.  
* User submitted files are uploaded and persisted to the server.
* No login
* Compile multiple files at the same time
* Job-management: see compile job's status (status and compile logs in real-time)
  * Download compiled .BSP

## Future features

* Packing custom assets automatically?
* Load-balancer middleware to spread compiler tasks across multiple computers?