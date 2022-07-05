from utils import *
import pandas as pd

XLSX_FILE = "RACK2022.xlsx"
SHEET_NAME = "DEVICES"

    

if __name__ == "__main__":


    # read file, and only use resources
    df = pd.read_excel(XLSX_FILE, sheet_name=SHEET_NAME)
    df_devices = df[df['is_resource']=="yes"]

    for index, row in df_devices.iterrows():

        # create data item based on defaults
        resourceIp = row["eth0 IP"] if row["eth0 IP"]!="-" else row["eth1 IP"]
        resourceHostname = row["hostname"] + ".local"
        
        if ping(resourceHostname):
            print(f"SUCCESS: Device '{row['UUID']}' with hostname '{resourceHostname}' is available via PING")
        else: 
            print(f"WARNING: Device '{row['UUID']}' with hostname '{resourceHostname}' is not available via PING")

            if not ping(resourceIp):
                print(f"WARNING: Device '{row['UUID']}' with IP '{resourceIp}' is not available via PING")
            else:
                print(f"SUCCESS: Device '{row['UUID']}' with IP '{resourceIp}' is available via PING")
