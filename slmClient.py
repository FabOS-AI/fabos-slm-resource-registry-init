import requests


DEFAULT_RESOURCE_ITEM = {
    "resourceHostname": "",
    "resourceIp": "",
    "resourceConnectionPort": 0
}

CAPABILITY_NAME_TO_ID = {
    "BASE" : "????",
    "DUMMY" : "2c8cafe5-1155-471c-9639-0db48ec249eb",
    "DOCKER": "08c5b8de-5d4a-4116-a73f-1d1f616c7c70",
    "TRANSFERAPP": "110d43ff-f351-4e55-92c0-77625875ce6e",
    "DOCKER_SWARM": "5dcb8fc8-556b-4735-9c80-fce546e7bd7a",
    "K3S": "21afb100-01f9-4915-9c8c-bf9afc032c01",
    "KUBERNETES": "a2ae8818-09ae-4e86-8e5a-2effb1122fa6"
}

class slmClient():
    """A client class for interaction with the SLM
    """
    def __init__(self, host, host_keycloak, host_resource_registry, slm_user, slm_password):
        self.host = host
        self.host_keycloak = host_keycloak
        self.host_resource_registry = host_resource_registry
        self.slm_user = slm_user
        self.slm_password = slm_password
        self.token = f"Bearer {self.get_keycloak_token()}"


    def get_keycloak_token(self) -> str:
        """Catch Bearer token from Keycloak
        Returns:
            str: bearer token as str
        """

        token_data = {
            "client_id": "self-service-portal",
            "grant_type": "password",
            "username": self.slm_user,
            "password": self.slm_password
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        res = requests.post(
            url=f"{self.host_keycloak}/auth/realms/fabos/protocol/openid-connect/token",
            data=token_data,
            headers=headers
        )

        if "access_token" in res.json().keys():
            print(f"SUCCESS({res.status_code}): got access_token from keycloak")
        else:
            print(f"ERORR({res.status_code}): can not get access_token from keycloak ({res.json()['error_description']}). Aborting...")
            exit(1)
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


    def create_resource(self, uuid:str, item) -> requests.models.Response:
        """Creates the resource for the given uuid

        Args:
            uuid (str): the uuid for the resource to be created
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

        # if item["resourceBaseConfiguration"]:
        #     item["resourceBaseConfiguration"] = CAPABILITY_NAME_TO_ID["BASE"]
        # else:
        #     del item["resourceBaseConfiguration"]

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): added resource '{uuid}' with config: {item}")
        else:
            print(f"FAILED({res.status_code}): added resource '{uuid}' with config: {item}: Response: {res.json()}")

        return res


    def add_capabilities(self, uuid:str, capabilities: list, overwrite:bool) -> requests.models.Response:
        """adds given capabilties to resource by given uuid

        Args:
            uuid (str): the resource to add the capabilities
            capabilities (list): a list of capabilities
            overwrite (bool): determines if an already registered capabilty is overwritten

        Returns:
            requests.models.Response: the raw http response
        """
        if capabilities:

            capability_options = ["DUMMY", "DOCKER", "TRANSFERAPP", "DOCKER_SWARM", "K3S"]

            # prepare requets
            headers = {
                'Authorization': self.token,
                'Realm': 'fabos'
            }

            # get already registered capability of given resource
            res_get = requests.get(
                url=f"{self.host_resource_registry}/resources/{uuid}/deployment-capabilities",
                headers=headers
            )

            # iterate through given capability candidates given
            for capability in capabilities:

                # filter if capability candidate is valid, else skip adding
                if capability in capability_options:

                    if len(res_get.json()) < 1:

                        print(f"Adding capability '{capability}' to resource '{uuid}'. Since resource has no capabilities yet")
                        res = self.add_capability(uuid=uuid, capability=capability)

                    else:
                        # parse fetched capabilties
                        parsed_available_capabilities = [ item['name'] for item in res_get.json()]

                        # add capability if already is registered but overwirte is True
                        if (capability in parsed_available_capabilities) and overwrite:
                            print(f"OVERWRITE: adding capability '{capability}' to resource '{uuid}'. Overwriting already available capbility!")
                            res = self.add_capability(uuid=uuid, capability=capability)

                        # add capability if specific capability is not already registered
                        elif capability not in parsed_available_capabilities:
                            print(f"Adding capability '{capability}' to resource '{uuid}'. Since resource has the capability not yet!")
                            res = self.add_capability(uuid=uuid, capability=capability)

                        # skip adding capbility
                        else:
                            print(f"SKIP: skipping adding capability '{capability}' to resource '{uuid}'. Since it already has the capbility and FORCE_OVERWRITE is not given!")
                            res = None

                else:
                    print(f"FAILED: capability '{capability}' not in available options {capability_options}. Skipping ...")
                    return None
            return res

        else:
            print(f"SKIP: adding capabilities skipped for resource '{uuid}' since no are given ...")
            return None

    def add_capability(self, uuid: str, capability: str) -> requests.models.Response:
        """Adds capability to resource

        Args:
            uuid (str): the uuid of the resource as str
            capability (str): the capability of the resource as str

        Returns:
            requests.models.Response: the raw request response OR None if failed
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }

        capabilityId = CAPABILITY_NAME_TO_ID[capability]
        res = requests.put(
            url=f"{self.host_resource_registry}/resources/{uuid}/capabilities?capabilityId={capabilityId}",
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): added capability '{capability}' for resource '{uuid}'")
            return res
        else:
            print(f"FAILED({res.status_code}): adding capability '{capability}' for resource '{uuid}'")
            print(res.text)
            return None

    def add_submodels(self, uuid: str, files: list) -> requests.models.Response:
        """Adds AAS submodels to resource

        Args:
            uuid (str): the uuid of the resource as str
            files (dict): a files dict of AASX file to add to the resource

        Returns:
            requests.models.Response: the raw request response OR None if failed
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }


        res = requests.post(
            url=f"{self.host_resource_registry}/resources/{uuid}/submodels",
            files=files,
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): added files '{files}' for resource '{uuid}'")
            return res
        else:
            print(f"FAILED({res.status_code}): adding files '{files}' for resource '{uuid}'")
            print(res.text)
            return None

    def get_resources(self) -> list:
        """Gets all resource from resource registry

        Returns:
            list: list of resource
        """
        
        print("refreshing token")
        self.token = f"Bearer {self.get_keycloak_token()}"
        print("token refreshed")

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

    def create_location(self, uuid:str, name:str) -> requests.models.Response:
        """Creates the location with the given uuid

        Args:
            uuid (str): the uuid of the location to be created
            name (str): the name of the location to be created

        Returns:
            requests.models.Response: the raw HTTP response
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }
        res = requests.post(
            url=f"{self.host_resource_registry}/resources/locations?id={uuid}&name={name}",
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): added location '{name}' ({uuid})")
        else:
            print(f"FAILED({res.status_code}): adding location '{name}' ({uuid})")
        return res
    
    def delete_location(self, uuid:str) -> requests.models.Response:
        """Deletes the location with the given uuid

        Args:
            uuid (str): the uuid of the location to be deleted

        Returns:
            requests.models.Response: the raw HTTP response
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }
        res = requests.delete(
            url=f"{self.host_resource_registry}/resources/locations?id={uuid}",
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): delete location '{uuid}'")
        else:
            print(f"FAILED({res.status_code}): adding location '{uuid}'")
        return res
    
    def get_locations(self) -> list:
        """Gets all locations from resource registry

        Returns:
            list: list of locations
        """

        headers = {
            'Authorization': self.token,
            'Realm': 'fabos'
        }
        res = requests.get(
            url=f"{self.host_resource_registry}/resources/locations",
            headers=headers
        )

        if res.status_code in [200, 201]:
            print(f"SUCCESS({res.status_code}): found '{len(res.json())}' location items")
        else:
            print(f"FAILED({res.status_code}): getting locations failed")

        return res.json()