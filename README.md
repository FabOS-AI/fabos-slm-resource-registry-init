# SLM ResourceRegistry Init

**Author**: [Lukas Rauh](https://github.com/luckyluks)    
**Short Description**: *A simple utility tool (REST-based) to initialize the registered resources and their capabilities in the SLM resource registry based on a table defined in an EXCEL sheet*

## Content:

This repo contains multiple utilty tools, as listed below:
```console
.
├── docker-compose.yaml: the easiest way to use the utility tool, a compose example, specifiying the environment variables
├── Dockerfile: the Dockerfile refered to in the 'docker-compose.yaml'
├── example.xlsx: the required EXCEL file to be used
├── getToken.py: another utility tool, to fetch a token from Keycloak
├── pingTest.py: another utility tool, to ping all listed resource in the EXCEL
├── README.md: this readme
├── requirements.txt: the required libraries to use the utility tools
├── setup.py: the main utility to add resources and their capabilities
├── slmClient.py: a simple SLM REST client implementation
└── utils.py: other utilitly function needed

```

## Usage

The easiest usage is through the provided Docker/Compose implementation. The container just wraps the environment around the Python scripts and allows to easily setup variables in the `docker-compose.yaml` file.

1. Add your resources, in the simplest way to the provided `example.xlsx`. Definitely required fields in the EXCEL are (per device):
   - "Device": an arbitrary device name, for easier reference
   - "user": the user name of the resource, in order to be accessed
   - a connection to the resource, in order to be accessed. Will only be added if "connection-type" different from "-" and contains:
     - "password": the password of the corresponding user
     - "hostname": the hostname of the resource
     - "connection-type": the connection type (typically one of: ssh, win-ssh, WinRm, http, tcp)
     - "connection-port": the port used for the connection-type
   - either "eth0 IP" or "eth1 IP": the IP of the resource, eth0 is always prefered
   - "is_resource" flage: determines if device is added to the resource registry. Set to "yes" in order to be added
   - "UUID": the UUID of the resource, can be generated externally
   - "location-uuid": the UUID of the location, where the resource is located
   - "aasx-filter-substring": a substring that is used to filter given AASX files in `/files` directory (see [AASX upload](#aasx-upload) )
   - capabilities to install:
     - "DC_Docker": if set to "yes", Docker capability will be added to resource
     - "DC_Transferapp": if set to "yes", Transferapp capability will be added to resource
     - "DC_Swarm": if set to "yes", Swarm capability will be added to resource
     - "DC_K3s": if set to "yes", K3s capability will be added to resource

2. Verify settings in the `docker-compose.yaml` file. To prevent errors, provide all, otherwise defaults will be used:
   - "SLM_HOST": the full domain name of the SLM host
   - "SLM_USER": the user to access the SLM
   - "SLM_PASSWORD": the password of the SLM user to access
   - "XLSX_FILE": the file with the resources specified
   - "SHEET_NAME": the sheet to be used, in the file with the resources specfied
   - behavior flags (use either "True"/"False"):
        - "FORCE_OVERWRITE": determines if resources and their capabilites should be overwritten if they already exist
        - "FORCE_DELETE": determines if a resources listed in the EXCEL sheet should be deleted in the first step
        - "DELETE_ALL": determines if all resources (not only listed resources in the EXCEL) should be deleted in the first step, to start with a clean resource registry
        - "PING_CHECK": determines if resources should be pinged before added to the resource registry
3. Build and start the tool with docker compose
    ```console
    docker compose up --build
    ```
    If you use an older version of docker, try `docker-compose up --build`


## AASX upload

1. put your AASX files into the `/files` subdirectory:

![image](https://user-images.githubusercontent.com/27732414/230616565-2aee9cba-4e64-4d94-b983-b06798c13f15.png)

2. use the `/files` property to filter the AASX files in the directory for every resource

![image](https://user-images.githubusercontent.com/27732414/230616752-ba1f2546-6055-4e49-a0fb-1fb580a67c54.png)


  **Hint:** AASX files will only be uploaded when resource exists in resource registry

## Outlook 

In the future the idea is to integrate the init procedure into the SLM base setup. Additionally a "resource wizard" could provide the same functionality in the UI of the SLM, adding the resources based on an EXCEL.
