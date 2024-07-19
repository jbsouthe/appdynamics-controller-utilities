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
        "requestFilter": getAppList(appd_controller_url, bearer),
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

def getDatabaseSummary(appd_controller_url, bearer):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    now = time.time()
    request_body = {
        "requestFilter": {},
        "resultColumns": ["ID", "NAME", "TYPE"],
        "offset": 0,
        "limit": -1,
        "searchFilters": [],
        "columnSorts": [{"column": "HEALTH", "direction": "ASC"}],
        "timeRangeStart": int(now) - (15 * 60000),
        "timeRangeEnd": int(now)
    }

    response = requests.post(
        f"{appd_controller_url}/controller/databasesui/databases/list?maxDataPointsPerMetric=1440",
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

def getServerList(appd_controller_url, bearer):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }
    now = time.time()
    request_body = {
        "filter": {
            "appIds": [],
            "nodeIds": [],
            "tierIds": [],
            "types": ["PHYSICAL", "CONTAINER_AWARE"],
            "timeRangeStart": int(now) - (15 * 60000),
            "timeRangeEnd": int(now)
        },
        "sorter": {
            "field": "HEALTH",
            "direction": "ASC"
        }
    }

    response = requests.post(
        f"{appd_controller_url}/controller/sim/v2/user/machines/keys",
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

def getServerHealth(appd_controller_url, bearer, machine_ids):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }
    request_body = {
        "timeRangeSpecifier": "last_1_hour.BEFORE_NOW.-1.-1.60",
        "machineIds": machine_ids
    }

    response = requests.post(
        f"{appd_controller_url}/controller/sim/v2/user/health",
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

def getServerMetrics(appd_controller_url, bearer, machine_ids):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }
    request_body = {
        "timeRange": "last_5_minutes.BEFORE_NOW.-1.-1.5",
        "ids": machine_ids,
        "metricNames": [
            "Hardware Resources|Machine|Availability",
            "Hardware Resources|Volumes|Used (%)",
            "Hardware Resources|CPU|%Busy",
            "Hardware Resources|CPU|%Stolen",
            "Hardware Resources|Memory|Used %",
            "Hardware Resources|Memory|Swap Used %",
            "Hardware Resources|Disks|Avg IO Utilization (%)",
            "Hardware Resources|Network|Avg Utilization (%)",
            "Hardware Resources|Load|Last 1 minute"
        ],
        "baselineId": None,
        "rollups": [1, 1440]
    }

    response = requests.post(
        f"{appd_controller_url}/controller/sim/v2/user/metrics/query/machines",
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

def getServerSummary(appd_controller_url, bearer):
    # Fetch the list of servers
    server_list = getServerList(appd_controller_url, bearer)
    machine_ids = [server["machineId"] for server in server_list.get("machineKeys", [])]

    # Fetch health and metrics data for the machines
    health_data = getServerHealth(appd_controller_url, bearer, machine_ids)
    metrics_data = getServerMetrics(appd_controller_url, bearer, machine_ids)

    # Combine data into a single dictionary
    combined_data = {}
    for server in server_list.get("machineKeys", []):
        machine_id = server["machineId"]
        combined_data[machine_id] = {
            "serverName": server["serverName"],
            "health": None,
            "metrics": {}
        }

    # Merge health data
    for machine_id, health in health_data.get("health", {}).items():
        if int(machine_id) in combined_data:
            combined_data[int(machine_id)]["health"] = health

    # Merge metrics data
    metrics_data_points = metrics_data.get("data", {}).get("1440", {})
    for machine_id, metrics in metrics_data_points.items():
        if int(machine_id) in combined_data:
            combined_data[int(machine_id)]["metrics"] = metrics.get("metricData", {})

    return combined_data

def main():
    parser = argparse.ArgumentParser(description="AppDynamics Configuration Script")
    parser.add_argument("-c", "--config", default="appdynamics-configuration.sh", help="Config file")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-t", "--type", default="applications", choices=["applications", "databases", "servers"], help="Type of data to retrieve")
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

    if args.type == "application":
        appData = getApplicationSummary(appd_controller_url, bearer)
        print(json.dumps(appData, indent=2))
    elif args.type == "database":
        dbData = getDatabaseSummary(appd_controller_url, bearer)
        print(json.dumps(dbData, indent=2))
    elif args.type == "servers":
        serverData = getServerSummary(appd_controller_url, bearer)
        print(json.dumps(serverData, indent=2))

if __name__ == "__main__":
    main()
