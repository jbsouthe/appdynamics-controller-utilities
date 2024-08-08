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
        f"{appd_controller_url}/controller/api/oauth/access_token",
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
    now = round(time.time()*1000)
    timeRangeStart = now - (15 * 60000)
    timeRangeEnd = now
    request_body = {
        "requestFilter": getAppList(appd_controller_url, bearer),
        "timeRangeStart": timeRangeStart,
        "timeRangeEnd": timeRangeEnd,
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

    data = response.json()
    minutes = round( (timeRangeEnd/60000) - (timeRangeStart/60000))
    for item in data['data']:
        item['deepLink'] = f"{appd_controller_url}/controller/#/location=APP_DASHBOARD&timeRange=Custom_Time_Range.BETWEEN_TIMES.{timeRangeEnd}.{timeRangeStart}.{minutes}&application={item['id']}&dashboardMode=force"
    return data

def getDatabaseSummary(appd_controller_url, bearer):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    now = round(time.time()*1000)
    timeRangeStart = now - (15 * 60000)
    timeRangeEnd = now
    request_body = {
        "requestFilter": {},
        "resultColumns": ["ID", "NAME", "TYPE"],
        "offset": 0,
        "limit": -1,
        "searchFilters": [],
        "columnSorts": [{"column": "HEALTH", "direction": "ASC"}],
        "timeRangeStart": timeRangeStart,
        "timeRangeEnd": timeRangeEnd
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

    health_data = response.json()
    database_ids = [item['configId'] for item in health_data['data']]
    metrics_data = fetch_database_data(appd_controller_url, bearer, database_ids)
    for item in metrics_data['data']:
        minutes = round( (timeRangeEnd/60000) - (timeRangeStart/60000))
        item['deepLink'] = f"{appd_controller_url}/controller/#/location=DB_MONITORING_SERVER_DASHBOARD&timeRange=Custom_Time_Range.BETWEEN_TIMES.{timeRangeEnd}.{timeRangeStart}.{minutes}&dbServerId={item['id']}"
    return metrics_data

# Function to fetch database data
def fetch_database_data(controller_url, token, database_ids):
    url = f"{controller_url}/controller/databasesui/databases/list/data?maxDataPointsPerMetric=1440"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*'
    }
    now = time.time()
    body = {
        "requestFilter": database_ids,
        "resultColumns": ["HEALTH", "QUERIES", "TIME_SPENT", "CPU"],
        "offset": 0,
        "limit": -1,
        "searchFilters": [],
        "columnSorts": [{"column": "TIME_SPENT", "direction": "DESC"}],
        "timeRangeStart": (int(now) - (15 * 60000))*1000,
        "timeRangeEnd": int(now)*1000
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code >= 300:
        print(f"Error: {response.status_code} - {response.text}")
        print("Request header:", json.dumps(headers, indent=2))
        print("Request body:", json.dumps(body, indent=2))
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

    now = round(time.time()*1000)
    timeRangeStart = now - (15 * 60000)
    timeRangeEnd = now
    minutes = round( (timeRangeEnd/60000) - (timeRangeStart/60000))
    # Combine data into a single dictionary
    combined_data = {}
    for server in server_list.get("machineKeys", []):
        machine_id = server["machineId"]
        combined_data[machine_id] = {
            "serverName": server["serverName"],
            "deepLink": f"{appd_controller_url}/controller/#/location=SERVER_MONITORING_MACHINE_OVERVIEW&timeRange=Custom_Time_Range.BETWEEN_TIMES.{timeRangeEnd}.{timeRangeStart}.{minutes}&machineId={machine_id}",
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


def getBusinessTransactionsSummary(appd_controller_url, bearer):
    applications = getAppList(appd_controller_url, bearer)
    now = round(time.time()*1000)
    timeRangeStart = now - (15 * 60000)
    timeRangeEnd = now
    minutes = round( (timeRangeEnd/60000) - (timeRangeStart/60000))
    btData = []
    for application in applications:
        appBTData = getApplicationBusinessTransactions(appd_controller_url, bearer, application)
        appBTData['deepLink'] = f"{appd_controller_url}/controller/#/location=APP_BT_LIST&timeRange=Custom_Time_Range.BETWEEN_TIMES.{timeRangeEnd}.{timeRangeStart}.{minutes}&application={appBTData['applicationEntity']['entityDefinition']['entityId']}"
        btData.append( {"application": appBTData})
    return btData

def getApplicationBusinessTransactions(appd_controller_url, bearer, application):
    url = f"{appd_controller_url}/controller/restui/v1/bt/listViewDataByColumnsV2"
    headers = {
        'Authorization': f'Bearer {bearer}',
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*'
    }
    now = round(time.time()*1000)
    timeRangeStart = now - (15 * 60000)
    timeRangeEnd = now
    minutes = round( (timeRangeEnd/60000) - (timeRangeStart/60000))
    body = {
        "requestFilter": {
            "queryParams": {
                "applicationIds": [application],
                "tags": []
            },
            "filterAll": False,
            "filters": []
        },
        "searchFilters": None,
        "timeRangeStart": timeRangeStart,
        "timeRangeEnd": timeRangeEnd,
        "columnSorts": None,
        "resultColumns": ["NAME","BT_HEALTH","AVERAGE_RESPONSE_TIME","CALL_PER_MIN","ERRORS_PER_MIN","PERCENTAGE_ERROR","PERCENTAGE_SLOW_TRANSACTIONS","PERCENTAGE_VERY_SLOW_TRANSACTIONS","PERCENTAGE_STALLED_TRANSACTIONS","END_TO_END_LATENCY_TIME","MAX_RESPONSE_TIME","MIN_RESPONSE_TIME","CALLS","SLOW_TRANSACTIONS","CPU_USED","TOTAL_ERRORS","BLOCK_TIME","WAIT_TIME","VERY_SLOW_TRANSACTIONS","STALLED_TRANSACTIONS"],
        "offset": 0,
        "limit": -1
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code >= 300:
        print(f"Error: {response.status_code} - {response.text}")
        print("Request header:", json.dumps(headers, indent=2))
        print("Request body:", json.dumps(body, indent=2))
    response.raise_for_status()
    data = response.json()
    for item in data['btListEntries']:
        item['deepLink'] = f"{appd_controller_url}/controller/#/location=APP_BT_DETAIL&timeRange=Custom_Time_Range.BETWEEN_TIMES.{timeRangeEnd}.{timeRangeStart}.{minutes}&application={application}&businessTransaction={item['id']}&dashboardMode=force"
    return data


def main():
    parser = argparse.ArgumentParser(description="AppDynamics Configuration Script")
    parser.add_argument("-c", "--config", default="appdynamics-configuration.sh", help="Config file")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-t", "--type", default="applications", choices=["applications", "databases", "servers", "business_transactions"], help="Type of data to retrieve")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    config = load_config(args.config)
    exec(config, globals())

    appd_controller_url = globals().get("APPD_CONTROLLER_URL")
    if appd_controller_url.endswith('/'):
        appd_controller_url = appd_controller_url[:-1]
    appd_client_id = globals().get("APPD_CLIENT_ID")
    appd_client_secret = globals().get("APPD_CLIENT_SECRET")

    if not all([appd_controller_url, appd_client_id, appd_client_secret]):
        print(f"Could not load AppDynamics Configuration from {args.config}, please set that up or something")
        exit(1)

    bearer = get_bearer_token(appd_controller_url, appd_client_id, appd_client_secret)

    if args.type == "applications":
        appData = getApplicationSummary(appd_controller_url, bearer)
        print(json.dumps(appData, indent=2))
    elif args.type == "databases":
        dbData = getDatabaseSummary(appd_controller_url, bearer)
        print(json.dumps(dbData, indent=2))
    elif args.type == "servers":
        serverData = getServerSummary(appd_controller_url, bearer)
        print(json.dumps(serverData, indent=2))
    elif args.type == "business_transactions":
        btData = getBusinessTransactionsSummary(appd_controller_url, bearer)
        print(json.dumps(btData, indent=2))

if __name__ == "__main__":
    main()
