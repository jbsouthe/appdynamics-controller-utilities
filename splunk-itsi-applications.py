import argparse
import logging
import requests
import json
import os
import time

def load_config(config_file):
    if not os.path.exists(config_file):
        print(f"Config file {config_file} does not exist")
        exit(1)
    with open(config_file) as f:
        config = f.read()
    return config

def get_bearer_token(appd_controller_url, appd_client_id, appd_client_secret):
    appd_account = appd_controller_url.split("/")[2].split(".")[0]
    response = requests.post(
        f"{appd_controller_url}controller/api/oauth/access_token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        auth=(appd_client_id, appd_client_secret),
        data={
            "grant_type": "client_credentials",
            "client_id": f"{appd_client_id}@{appd_account}",
            "client_secret": appd_client_secret
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]

def getAppList(appd_controller_url, bearer):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    now = time.time()
    request_body = {
        "requestFilter": {
            "filters":[{"field":"TYPE","criteria":"APM","operator":"EQUAL_TO"}],
            "filterAll" : False,
            "queryParams": {"applicationIds":[],"tags":[]}
        },
        "searchFilters":[],
        "timeRangeStart": now - (15 * 60000),
        "timeRangeEnd": now,
        "columnSorts": [{"column":"APP_OVERALL_HEALTH","direction":"DESC"}],
        "resultColumns":["NAME"],
        "offset":0,
        "limit":-1
    }

    response = requests.post(
        f"{appd_controller_url}/controller/restui/v1/app/list/all",
        headers=request_headers,
        json=request_body
    )

    if response.status_code >= 300:
        print(f"Error: {response.status_code} - {response.text}")
        # Print the request body for debugging
        print("Request header:", json.dumps(request_headers, indent=2))
        print("Request body:", json.dumps(request_body, indent=2))

    response.raise_for_status()
    return response.json()['data']

def getApplicationSummary(appd_controller_url, bearer):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    now = time.time()
    request_body = {
        "requestFilter": getAppList( appd_controller_url, bearer),
        "timeRangeStart": now - (15 * 60000),
        "timeRangeEnd": now,
        "searchFilters": None,
        "columnSorts": None,
        "resultColumns": ["APP_OVERALL_HEALTH","CALLS","CALLS_PER_MINUTE","AVERAGE_RESPONSE_TIME","ERROR_PERCENT","ERRORS","ERRORS_PER_MINUTE","NODE_HEALTH","BT_HEALTH"],
        "offset":0,
        "limit":-1
    }

    response = requests.post(
        f"{appd_controller_url}/controller/restui/v1/app/list/ids",
        headers=request_headers,
        json=request_body
    )

    if response.status_code >= 300:
        print(f"Error: {response.status_code} - {response.text}")
        # Print the request body for debugging
        print("Request header:", json.dumps(request_headers, indent=2))
        print("Request body:", json.dumps(request_body, indent=2))

    response.raise_for_status()
    return response.json()



def main():
    parser = argparse.ArgumentParser(description="AppDynamics Configuration Script")
    parser.add_argument("-c", "--config", default="appdynamics-configuration.sh", help="Config file")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    config = load_config(args.config)
    exec(config, globals())

    appd_controller_url = globals().get("APPD_CONTROLLER_URL")
    appd_client_id = globals().get("APPD_CLIENT_ID")
    appd_client_secret = globals().get("APPD_CLIENT_SECRET")

    if not all([appd_controller_url, appd_client_id, appd_client_secret]):
        print(f"Could not load AppDynamics Configuration from {args.config}, please set that up or something")
        exit(1)

    bearer = get_bearer_token(appd_controller_url, appd_client_id, appd_client_secret)
    appData = getApplicationSummary(appd_controller_url, bearer)
    print(json.dumps(appData, indent=2))

if __name__ == "__main__":
    main()
