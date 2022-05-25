import time
import pandas as pd
import json
import requests

DEFAULT_RESOURCE_ITEM = {
    "resourceHostname": "",
    "resourceIp": "",
    "resourceUsername": "",
    "resourcePassword": "",
    "checkResource": False,
    "sshAccessAvailable": True
}


class slmClient():
    def __init__(self, host, host_keycloak, host_resource_registry):
        self.host = host
        self.host_keycloak = host_keycloak
        self.host_resource_registry = host_resource_registry
        self.token = f"Bearer {self.get_keycloak_token()}"


    def get_keycloak_token(self) -> str:
        """Catch Bearer token from Keycloak
        Returns:
            str: bearer token as str
        """

        token_data = {
            "client_id":"self-service-portal",
            "grant_type":"password",
            "username":"fabos",
            "password":"password"
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        res = requests.post(
            url=f"{self.host_keycloak}/auth/realms/fabos/protocol/openid-connect/token",
            data=token_data,
            headers=headers
        )

        if "access_token" in res.json().keys():
            print(f"SUCCESS({res.status_code}): got access_token from keycloak")

        return res.json()["access_token"]


    def delete_resource(self, uuid:str) -> requests.models.Response:
        """Deletes the resource for the given UUID at the resource registry
        Args:
            uuid (str): the uuid of the resource to be deleted
        Returns:
            requests.models.Response: the raw HTTP response
        """

        headers={
            'Authorization': self.token,
            'Realm': 'fabos'
        }

        res = requests.delete(
            url=f"{self.host_resource_registry}/resources/{uuid}",
            headers=headers
            #data={
            #    
            #},
        )

        if res.status_code == 200:
            print(f"SUCCESS({res.status_code}): removed resource '{uuid}'")
        else:
            print(f"FAILED({res.status_code}): removed resource '{uuid}'")

        return res


    def create_resource(self, uuid:str, capabilities: list, item) -> requests.models.Response:
        """Creates the resource for the given uuid, item and capabilities

        Args:
            uuid (str): the uuid for the resource to be created
            capabilities (list): a list of capabilities to be set additionally
            item (_type_): the item to be used for the creation

        Returns:
            requests.models.Response: the raw HTTP response
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }
        res = requests.put(
            url=f"{self.host_resource_registry}/resources/{uuid}",
            data=item,
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): added resource '{uuid}' with config: {item}")
        else:
            print(f"FAILED({res.status_code}): added resource '{uuid}' with config: {item}")

        if capabilities:

            capability_options = ["SHELL", "DOCKER", "TRANSFERAPP", "DOCKER_SWARM", "K3S"]

            for capability in capabilities:

                if capability in capability_options:

                    print("pause for registry to breath")
                    time.sleep(4)

                    headers = {
                        'Authorization': self.token,
                        'Realm': 'fabos'
                    }
                    res = requests.put(
                        url=f"{self.host_resource_registry}/resources/{uuid}/deployment-capabilities?deploymentCapability={capability}",
                        headers=headers
                    )

                    if res.status_code in [200, 201]:
                        print(f"SUCCESS({res.status_code}): added capability '{capability}' for resource '{uuid}'")
                    else:
                        print(f"FAILED({res.status_code}): adding capability '{capability}' for resource '{uuid}'")
                        print(res.text)

                else:
                    print(f"FAILED: capability '{capability}' not in {capability_options}. Skipping ...")
        return res
    
    def get_resources(self) -> list:
        """Gets all resource from resource registry

        Returns:
            list: list of resource
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }
        res = requests.get(
            url=f"{self.host_resource_registry}/resources",
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): found '{len(res.json())}' resource items")
        else:
            print(f"FAILED({res.status_code}): getting resources failed")

        return res.json()

    def get_resource(self, uuid:str) -> object:
        """Gets the resource for the given uuid at resource registry

        Args:
            uuid (str): the uuid to lookup

        Returns:
            object: the resource object, if available
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }
        res = requests.get(
            url=f"{self.host_resource_registry}/resources/{uuid}",
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): found resource '{uuid}' in registry")
            return res.json()
        else:
            print(f"FAILED({res.status_code}): could not found resource '{uuid}' in registry")
            return {}

        
