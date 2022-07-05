import os
import time
import json
import requests
import pandas as pd
from slmClient import *
from utils import *
from argparse import ArgumentParser


# read variables from environment or use defaults
SLM_HOST = str(os.getenv("SLM_HOST", "http://192.168.153.47"))
SLM_USER = str(os.getenv("SLM_USER", "fabos"))
SLM_PASSWORD = str(os.getenv("SLM_PASSWORD", "password"))
RESOURCE_REGISTRY_HOST = str(os.getenv("RESOURCE_REGISTRY_HOST", f"{SLM_HOST}:9010"))
KEYCLOAK_HOST = str(os.getenv("KEYCLOAK_HOST", f"{SLM_HOST}:7080"))
XLSX_FILE = str(os.getenv("XLSX_FILE", "example.xlsx"))
SHEET_NAME = str(os.getenv("SHEET_NAME", "DEVICES"))
FORCE_OVERWRITE = os.getenv("FORCE_OVERWRITE", "False")
FORCE_DELETE = os.getenv("FORCE_DELETE", "False")
DELETE_ALL = os.getenv("DELETE_ALL", "False")
PING_CHECK = os.getenv("PING_CHECK", "False")

# print variables
print("RESOURCE REGISTRY INIT: CONFIG SUMMARY (environment or defaults) ----------------------------------------------------------")
print("SLM_HOST: ", SLM_HOST)
print("SLM_USER: ", SLM_USER)
print("SLM_PASSWORD: ", SLM_PASSWORD)
print("RESOURCE_REGISTRY_HOST: ", RESOURCE_REGISTRY_HOST)
print("KEYCLOAK_HOST: ", KEYCLOAK_HOST)
print("XLSX_FILE: ", XLSX_FILE)
print("SHEET_NAME: ", SHEET_NAME)
print("FORCE_OVERWRITE: ", FORCE_OVERWRITE)
print("FORCE_DELETE: ", FORCE_DELETE)
print("DELETE_ALL: ", DELETE_ALL)
print("PING_CHECK: ", PING_CHECK)
print("RESOURCE REGISTRY INIT:----------------------------------------------------------------------------------------------------")


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


def main(args):
    """The main function to add resources and their capabilites
    Args:
        args (argparse arguments): the parsed args
    """

    # check if EXCEL file exists
    if not os.path.exists(XLSX_FILE):
        print(f"ERORR: file '{XLSX_FILE}' does not exist. Please either add the file or change environment variable 'XLSX_FILE' accordingly!")
        exit(1)
    # read file, and only use resources
    df = pd.read_excel(XLSX_FILE, sheet_name=SHEET_NAME)
    df_devices = df[df['is_resource']=="yes"]

    # get slm client instance
    slm = slmClient(
        host=SLM_HOST, 
        host_keycloak=KEYCLOAK_HOST, 
        host_resource_registry=RESOURCE_REGISTRY_HOST,
        slm_user=SLM_USER,
        slm_password=SLM_PASSWORD
    )
    
    # setup empty summary cache arrays
    resources_added = []
    resources_accessible = []
    resources_capabilities_added = []
    resources_deleted = []


    # start with deleting all (currently available) resources, IF FORCE_DELETE is set
    if FORCE_DELETE == 'True':
        print(f"\nStarting resource clean up (DELETE_ALL={DELETE_ALL}, FORCE_DELETE={FORCE_DELETE}):-----------------------------------------------------------")
        for resource in slm.get_resources():

                # ensure resource will be added again, skip this if DELETE_ALL is set to True
                if DELETE_ALL == 'True':
                        slm.delete_resource(uuid=resource["id"])
                        resources_deleted.append(f"{resource['id']}, {resource['hostname']}, {resource['ip']}")
                else:
                        if resource["id"] in df["UUID"].tolist():
                                slm.delete_resource(uuid=resource["id"])
                                resources_deleted.append(f"{resource['id']}, {resource['hostname']}, {resource['ip']}")
                        else:
                                print(f"Skipped deleting resource '{resource['id']}' since it is not in source file '{XLSX_FILE}'")

        print("pause for registry to breath (long - 5s) ... will continue with adding resources\n------------------------------------------------------------------------")
        time.sleep(5)


    print(f"\nStarting resource creation (FORCE_OVERWRITE={FORCE_OVERWRITE}):------------------------------------------------------------------------")
    # get already available resources first
    resources_current = [resource["id"] for resource in slm.get_resources()]
    # iterate through given resources from EXCEL
    for index, row in df_devices.iterrows():
        # create data item based on defaults
        device_resource_item = DEFAULT_RESOURCE_ITEM.copy()
        device_resource_item["resourceIp"] = row["eth0 IP"] if row["eth0 IP"]!="-" else row["eth1 IP"]
        device_resource_item["resourceUsername"] = row["user"]
        device_resource_item["resourcePassword"] = row["password"]
        device_resource_item['resourceHostname'] = row["hostname"]

        # check if hostname is available, IF PING_CHECK is set
        if PING_CHECK == "True":

                # ping hostname
                if not ping(device_resource_item['resourceHostname']):
                        print(f"WARNING: Device '{row['UUID']}' with hostname '{device_resource_item['resourceHostname']}' is not available via PING!")
                
                # additional IP ping test
                if not ping(device_resource_item["resourceIp"]):
                        print(f"ERROR: Device '{row['UUID']}' with IP '{device_resource_item['resourceIp']}' is not available via PING. Aborting setup!")
                        break
                resources_accessible.append(f"{row['UUID']}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")

        # if resource already exists, check the FORCE_OVERWRITE argument, else create directly
        if row['UUID'] in resources_current:
                if (args.force) or (FORCE_OVERWRITE == 'True'):
                        print(f"WARNING: overwriting resource '{row['UUID']}' since it already exists")
                        print(slm.create_resource(uuid=row["UUID"], item=device_resource_item))
                        resources_added.append(f"{row['UUID']}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")
                else:
                        print(f"WARNING: skipped overwriting resource '{row['UUID']}' since parameter '-f' was not given!")
        else:
                print(slm.create_resource(uuid=row["UUID"], item=device_resource_item))
                resources_added.append(f"{row['UUID']}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")
        
        # print("pause for registry to breath")
        # time.sleep(1)
        print("------------------------------------------------------------------------")

    # only wait if resources were added, else continue direclty
    if len(resources_added)  > 0:
        print("pause for registry to breath (long - 20s) ... will continue with adding capabilities\n------------------------------------------------------------------------")
        time.sleep(20)
    

    print(f"\nChecking available resources:----------------------------------------------------------------------------------------------")
    resources_current = [resource["id"] for resource in slm.get_resources()]
    if len(resources_current) > 0:
        print(f"'{len(resources_current)}' resources are available. Continuing with adding capabilities...")
    else:
        print(f"'{len(resources_current)}' resources are available. Additionally waiting 20s for resources...")
        time.sleep(20)
        print(f"Checking available resources again")
        resources_current = [resource["id"] for resource in slm.get_resources()]
        if len(resources_current) > 0:
                print(f"'{len(resources_current)}' resources are available. Continuing with adding capabilities...")
        else:
                print(f"ERROR: '{len(resources_current)}' resources are available. Continuing, but expecting failure!")


    print(f"\nStarting adding capabilities:----------------------------------------------------------------------------------------------")
    resources_current = [resource["id"] for resource in slm.get_resources()]
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

        if row["UUID"] in resources_current:
                res = slm.add_capabilities(
                        uuid=row["UUID"],
                        capabilities=capabilities,
                        overwrite=(args.force) or (FORCE_OVERWRITE == 'True')
                )
                
                # only add capabilties to list if result is provided (implies that request succeeded)
                if res:
                        print(res)
                        resources_capabilities_added.append(f"{row['UUID']}, {row['hostname']}, {capabilities}")
        else:
                print(f"FAILED: cannot add capabilities to resource {row['UUID']} since it is not registered at the registry (yet). Skipping...")

        # print("pause for registry to breath")
        # time.sleep(1)
        print("------------------------------------------------------------------------")

    # finish
    print("\nSUMMARY -------------------------------------------------------------------------------------------------------------------")
    print(f"Resources deleted (via REST): {json.dumps(resources_deleted, indent=2)}")
    print(f"Resources accessible (via ping): {json.dumps(resources_accessible, indent=2)}")
    print(f"Resources added to registry (via REST): {json.dumps(resources_added, indent=2)}")
    print(f"Capabilities added to resources (via REST): {json.dumps(resources_capabilities_added, indent=2)}")
    print("Resource Registry Setup Done!")
    print(f"Took: {(time.time()-start_time):.2f}s")
    

if __name__ == "__main__":

    # register start time
    start_time=time.time()

    # Grab command line args
    args = build_argparser().parse_args()

    # start main
    main(args)
    exit(0)
