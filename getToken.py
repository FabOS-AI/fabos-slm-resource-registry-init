import requests
import pyperclip

SLM_HOST = "http://192.168.153.47"
RESOURCE_REGISTRY_HOST = f"{SLM_HOST}:9010"
KEYCLOAK_HOST = f"{SLM_HOST}:7080"


def get_keycloak_token() -> str:

    token_data = {
        "client_id":"self-service-portal",
        "grant_type":"password",
        "username":"fabos",
        "password":"password"
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    res = requests.post(
        url=f"{KEYCLOAK_HOST}/auth/realms/fabos/protocol/openid-connect/token",
        data=token_data,
        headers=headers
    )

    return res.json()["access_token"]


if __name__ == "__main__":


    # get a token
    token_raw = get_keycloak_token()
    print(f"using token: {token_raw}")
 
    pyperclip.copy(token_raw)
    print("copied to clipboard!")