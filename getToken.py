import requests
import pyperclip

SLM_HOST = "http://192.168.153.47"
KEYCLOAK_HOST = f"{SLM_HOST}:7080"


def get_keycloak_token(host: str, user:str, password:str) -> str:

    token_data = {
        "client_id": "self-service-portal",
        "grant_type": "password",
        "username": user,
        "password": password
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        res = requests.post(
            url=f"{host}/auth/realms/fabos/protocol/openid-connect/token",
            data=token_data,
            headers=headers
        )
        return res.json()["access_token"]

    except KeyError:
        print(
            f"Keycloak response from keycloak host '{host}' did not contained an 'access_key'.\n",
            f"Error: {res.json()['error_description']}\n",
            f"Returning 'None'..."
        )
        return None
    except Exception as e:
        print(f"Could not fetch token from keycloak host '{host}'. Error: {type(e)}: {e} Returning 'None'...")
        return None


if __name__ == "__main__":

    # get a token
    token_raw = get_keycloak_token(KEYCLOAK_HOST, "fabos", "password")

    if token_raw is not None:
        print(f"token: {token_raw}")
    
        try:
            pyperclip.copy(token_raw)
            print("copied to clipboard!")
        except:
            print(f"Could not copy token to clipboar automatically. Please do it manually...")