import os
import glob
import time
import json
import uuid
from argparse import ArgumentParser

import pandas as pd

from slmClient import *
from utils import *

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
GENERATE_UUID = os.getenv("GENERATE_UUID", "False")
AASX_FILE_FILTER = os.getenv("AASX_FILE_FILTER", "/files/**/*.aasx")

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
print("GENERATE_UUID: ", GENERATE_UUID)
print("AASX_FILE_FILTER: ", AASX_FILE_FILTER)
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

    print(f"\nLoading data (XLSX_FILE='{XLSX_FILE}', SHEET_NAME='{SHEET_NAME}') ----------------------------------------------------------")
    # check if EXCEL file exists
    if not os.path.exists(XLSX_FILE):
        print(f"ERORR: file '{XLSX_FILE}' does not exist. Please either add the file or change environment variable 'XLSX_FILE' accordingly!")
        exit(1)
    # read file, and only use resources
    sheet_names = pd.ExcelFile(XLSX_FILE).sheet_names 
    
    if SHEET_NAME in sheet_names:
        df = pd.read_excel(XLSX_FILE, sheet_name=SHEET_NAME)
        df_devices = df[df['is_resource']=="yes"]
        print(f"Loaded '{len(df_devices)}' devices from sheet '{SHEET_NAME}' in file '{XLSX_FILE}'")
    else:
        print("ERORR: sheet name '{SHEET_NAME}' does not exist in file '{XLSX_FILE}'. Cannot process device data!")

    if "LOCATIONS" in sheet_names:
        df_locations = pd.read_excel(XLSX_FILE, sheet_name="LOCATIONS")
        print(f"Loaded '{len(df_locations)}' devices from sheet 'LOCATIONS' in file '{XLSX_FILE}'")
    else:
        print("ERORR: sheet name 'LOCATIONS' does not exist in file '{XLSX_FILE}'. Cannot process location data!")    

    # setup empty summary cache arrays
    resources_added = []
    resources_accessible = []
    resources_capabilities_added = []
    resources_deleted = []
    locations_added = []
    aasxs_added = []

    # get current state
    print("\nFetching current state (resources, locations) ----------------------------------------------------------")
    slm = slmClient(
        host=SLM_HOST,
        host_keycloak=KEYCLOAK_HOST,
        host_resource_registry=RESOURCE_REGISTRY_HOST,
        slm_user=SLM_USER,
        slm_password=SLM_PASSWORD
    )
    locations_current = slm.get_locations()
    resources_current = [resource["id"] for resource in slm.get_resources()]

    # add locations
    if DELETE_ALL == 'True':
        print(f"\nStarting locations clean up (DELETE_ALL={DELETE_ALL}):---------------------------------------------------------------------------------------")
        for location_item in locations_current:
            slm.delete_location(uuid=location_item['id'])
    
    if len(df_locations) > 0:
        print(f"\nStarting adding locations (in total '{len(df_locations)}' locations):---------------------------------------------------------------")
        for index, row in df_locations.iterrows():
            if slm.create_location(row["UUID"], row["Name"]):
                locations_added.append(f'{row["Name"]} ({row["UUID"]})')
    locations_current = [location["id"] for location in slm.get_locations()] 



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
        device_resource_item['resourceHostname'] = row["hostname"]

        if row["connection-type"] != "-":
            device_resource_item["resourceUsername"] = row["user"]
            device_resource_item["resourcePassword"] = row["password"]
            device_resource_item['resourceConnectionType'] = row["connection-type"]
            device_resource_item['resourceConnectionPort'] = round(row["connection-port"])
        
        if row["location-uuid"]:
            device_resource_item["resourceLocation"] = row["location-uuid"]
            if not row["location-uuid"] in locations_current:
                print(f"WARNING: Location uuid '{row['location-uuid']}' for resource '{device_resource_item['resourceHostname']}' not registered yet... But proceed adding resource")

        # # add flag for install of BaseConfigCapability (aka. FabOS Device Capability) - True/False
        # device_resource_item['resourceBaseConfiguration'] = "DC_Base" in row.keys() and row["DC_Base"] == "yes"
               

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
            uuid_str = str(uuid.uuid4()) if GENERATE_UUID == "True" else row['UUID']
            print(slm.create_resource(uuid=uuid_str, item=device_resource_item))
            resources_added.append(f"{uuid_str}, {device_resource_item['resourceHostname']}, {device_resource_item['resourceIp']}")
        
        # print("pause for registry to breath")
        time.sleep(0.3)
        print("------------------------------------------------------------------------")

    # only wait if resources were added, else continue direclty
    if len(resources_added)  > 0:
        print("pause for registry to breath (long - 10s) ... will continue with adding capabilities\n------------------------------------------------------------------------")
        time.sleep(10)


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
        if "DC_Dummy" in row.keys() and row["DC_Dummy"] == "yes":
            capabilities.append("DUMMY")
        if "DC_Docker" in row.keys() and row["DC_Docker"] == "yes":
            capabilities.append("DOCKER")
        if "DC_Transferapp" in row.keys() and row["DC_Transferapp"] == "yes":
            capabilities.append("TRANSFERAPP")
        if "DC_Swarm" in row.keys() and row["DC_Swarm"] == "yes":
            capabilities.append("DOCKER_SWARM")
        if "DC_K3S" in row.keys() and row["DC_K3S"] == "yes":
            capabilities.append("K3S")

        if not len(capabilities) > 0:
            print(f"WARN: no capabilities parse for resource '{row['UUID']}'. Will skip call to add ...")      
            print("------------------------------------------------------------------------")
            continue

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

        print("pause for registry to breath (long - 5s) ... will continue with adding aasx submodels\n------------------------------------------------------------------------")
        time.sleep(5)

    print(f"\nStarting adding aasx submodels:----------------------------------------------------------------------------------------------")
    resources_current = [resource["id"] for resource in slm.get_resources()]
    aasx_files = glob.glob(AASX_FILE_FILTER, recursive=True)
    print(f"Found '{len(aasx_files)}' AASX file(s) for filter '{AASX_FILE_FILTER}' ...\n")

    for index, row in df_devices.iterrows():

        # parse aasx files

        capabilities = []
        if "aasx-filter-substring" in row.keys() and len(str(row["aasx-filter-substring"])) > 0 and str(row["aasx-filter-substring"]) != "nan":
            paths = [aasx_path for aasx_path in aasx_files if str(row["aasx-filter-substring"]) in aasx_path]
            files = [("aasx", open(path, 'rb')) for path in paths]
            print(f"Found '{len(paths)}' aasx files matching given filter substring '{str(row['aasx-filter-substring'])}' for resource '{row['UUID']}' ...")

        else:
            print(f"WARN: no aasx files filter (aasx-filter-substring) available for for resource '{row['UUID']}'. Will skip to add submodels ...")      
            print("------------------------------------------------------------------------")
            continue

        if row["UUID"] in resources_current:

            for file_item in files:
                res = slm.add_submodels(
                    uuid=row["UUID"],
                    files=[file_item]
                )
                time.sleep(3)

                # only add submodels to list if result is provided (implies that request succeeded)
                if res:
                    aasxs_added.append(f"{row['UUID']}, {file_item}")
        else:
            print(f"FAILED: cannot add aasx submodels to resource {row['UUID']} since it is not registered at the registry (yet). Skipping...")
        print("------------------------------------------------------------------------")
        time.sleep(1)


    # finish
    print("\nSUMMARY -------------------------------------------------------------------------------------------------------------------")
    print(f"Resources deleted (via REST): {json.dumps(resources_deleted, indent=2)}")
    print(f"Resources accessible (via ping): {json.dumps(resources_accessible, indent=2)}")
    print(f"Locations added to registry (via REST): {json.dumps(locations_added, indent=2)}")
    print(f"Resources added to registry (via REST): {json.dumps(resources_added, indent=2)}")
    print(f"Capabilities added to resources (via REST): {json.dumps(resources_capabilities_added, indent=2)}")
    print(f"AAS submodels added to resources (via REST): {json.dumps(aasxs_added, indent=2)}")
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
