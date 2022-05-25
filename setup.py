import os
import time
import json
import requests
import pandas as pd
from slmClient import *
from utils import *
from argparse import ArgumentParser

SLM_HOST = str(os.getenv("SLM_HOST", "http://192.168.153.47"))
RESOURCE_REGISTRY_HOST = str(os.getenv("RESOURCE_REGISTRY_HOST", f"{SLM_HOST}:9010"))
KEYCLOAK_HOST = str(os.getenv("KEYCLOAK_HOST", f"{SLM_HOST}:7080"))
XLSX_FILE = str(os.getenv("XLSX_FILE", "RACK2022.xlsx"))
SHEET_NAME = str(os.getenv("SHEET_NAME", "DEVICES"))
FORCE_OVERWRITE = os.getenv("FORCE_OVERWRITE", "False")
FORCE_DELETE = os.getenv("FORCE_DELETE", "True")

print("RESOURCE REGISTRY INIT: CONFIG SUMMARY -----------------------")
print("SLM_HOST: ", SLM_HOST)
print("RESOURCE_REGISTRY_HOST: ", RESOURCE_REGISTRY_HOST)
print("KEYCLOAK_HOST: ", KEYCLOAK_HOST)
print("XLSX_FILE: ", XLSX_FILE)
print("SHEET_NAME: ", SHEET_NAME)
print("FORCE_OVERWRITE: ", FORCE_OVERWRITE)
print("FORCE_DELETE: ", FORCE_DELETE)
print("RESOURCE REGISTRY INIT:---------------------------------------")
# exit(137)



def build_argparser():
    """
    Parse command line arguments.
    :return: command line arguments
    """
    parser = ArgumentParser()
    parser.add_argument("-f", "--force", default=False, action="store_true",
                        help="(optional) Force overwrite of resources, at creation"
                        "WARNING: this can cause problems in the resource registry!")

    return parser



if __name__ == "__main__":

    # Grab command line args
    args = build_argparser().parse_args()

    # get client instance
    slm = slmClient(
        host=SLM_HOST, 
        host_keycloak=KEYCLOAK_HOST, 
        host_resource_registry=RESOURCE_REGISTRY_HOST
    )

    # read file, and only use resources
    df = pd.read_excel(XLSX_FILE, sheet_name=SHEET_NAME)
    df_devices = df[df['is_resource']=="yes"]
    
    print("INFO: starting device creation")
    start_time=time.time()
    
    resources_added = []
    resources_accessible = []
    resources_capabilities_added = []
#     for index, row in df_devices.iterrows():

        

#         # create data item based on defaults
#         device_resource_item = DEFAULT_RESOURCE_ITEM.copy()
#         device_resource_item["resourceIp"] = row["eth0 IP"] if row["eth0 IP"]!="-" else row["eth1 IP"]
#         device_resource_item["resourceUsername"] = row["user"]
#         device_resource_item["resourcePassword"] = row["password"]

#         # check if hostname is available
#         if not ping(row["hostname"] + ".local"):
#                 print(f"WARNING: Device '{row['UUID']}' with hostname '{row['hostname']+'.local'}' is not available via PING!")
#         device_resource_item["resourceHostname"] = row["hostname"] + ".local"

#         # additional IP ping test
#         if not ping(device_resource_item["resourceIp"]):
#             print(f"ERROR: Device '{row['UUID']}' with IP '{device_resource_item['resourceIp']}' is not available via PING. Aborting setup!")
#             break
#         resources_accessible.append(f"{row['UUID']}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")

#         # delete resource first
#         if FORCE_DELETE == 'True':
#                 slm.delete_resource(uuid=row["UUID"])
#                 print("pause for registry to breath")
#                 time.sleep(4)
#                 print(slm.create_resource(uuid=row["UUID"], item=device_resource_item))
#                 resources_added.append(f"{row['UUID']}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")

#         elif slm.get_resource(row['UUID']):

#                 if (args.force) or (FORCE_OVERWRITE == 'True'):
#                         print(f"WARNING: overwriting resource '{row['UUID']}' since it already exists")
#                         print(slm.create_resource(uuid=row["UUID"], item=device_resource_item))
#                         resources_added.append(f"{row['UUID']}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")
#                 else:
#                         print(f"WARNING: skipped overwriting resource '{row['UUID']}' since parameter '-f' was not given!")
#         else:
#                 print(slm.create_resource(uuid=row["UUID"], item=device_resource_item))
#                 resources_added.append(f"{row['UUID']}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")
        
#         print("pause for registry to breath\n----------------------------------------------------")
#         time.sleep(1)
    
    print("pause for registry to breath (long)\n----------------------------------------------------")
    time.sleep(10)

    
    print("INFO: starting adding capabilities")
    for index, row in df_devices.iterrows():

        

        # parse capabilities
        capabilities = []
        if "DC_Docker" in row.keys() and row["DC_Docker"] == "yes":
                capabilities.append("DOCKER")
        if "DC_Transferapp" in row.keys() and row["DC_Transferapp"] == "yes":
                capabilities.append("TRANSFERAPP")
        if "DC_Swarm" in row.keys() and row["DC_Swarm"] == "yes":
                capabilities.append("DOCKER_SWARM")
        if "DC_K3S" in row.keys() and row["DC_K3S"] == "yes":
                capabilities.append("K3S")

        if slm.get_resource(row['UUID']):
                print(slm.add_capabilities(uuid=row["UUID"], capabilities=capabilities))
                resources_capabilities_added.append(f"{row['UUID']}, {row['hostname']}, {capabilities}")

        print("pause for registry to breath\n----------------------------------------------------")
        time.sleep(1)
    
    # finish
    print("SUMMARY ----------------------------------------------------")
    print(f"Resources accessible (via ping): {json.dumps(resources_accessible, indent=2)}")
    print(f"Resources added to registry (via REST): {json.dumps(resources_added, indent=2)}")
    print(f"Capabilities added to resources (via REST): {json.dumps(resources_capabilities_added, indent=2)}")
    print("Resource Registry Setup Done!")
    print(f"Took: {(time.time()-start_time):.2f}s")
    exit(0)