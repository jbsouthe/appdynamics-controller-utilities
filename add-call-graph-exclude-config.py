import argparse
import requests
import json
import os

PACKAGE = "com.john"
DESCRIPTION = "test for john"

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

def get_application_id(appd_controller_url, bearer, appname):
    response = requests.get(
        f"{appd_controller_url}controller/rest/applications?output=JSON",
        headers={"Authorization": f"Bearer {bearer}"}
    )
    response.raise_for_status()
    apps = response.json()
    for app in apps:
        if app["name"] == appname:
            return app["id"]
    return None

def get_app_configuration(appd_controller_url, bearer, app_id):
    response = requests.get(
        f"{appd_controller_url}controller/restui/applicationManagerUiBean/applicationConfiguration/{app_id}",
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*"
        }
    )
    response.raise_for_status()
    return response.json()

def save_app_configuration(appd_controller_url, bearer, app_id, agent_type, config):
    request_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
    }
    request_body = {
        "agentType": agent_type,
        "applicationId": app_id,
        "config": config
    }

    response = requests.post(
        f"{appd_controller_url}controller/restui/configuration/callGraph/save",
        headers=request_headers,
        json=request_body
    )

    if response.status_code >= 300:
        print(f"Error: {response.status_code} - {response.text}")
        # Print the request body for debugging
        print("Request header:", json.dumps(request_headers, indent=2))
        print("Request body:", json.dumps(request_body, indent=2))

    response.raise_for_status()
    return

def add_excluded_package(name, desc, config):
    package = f"name={name},description={desc},system=false"
    if "excludedPackages" not in config:
        config["excludedPackages"] = []
    if package not in config["excludedPackages"]:
        config["excludedPackages"].append(package)
    return config

def remove_excluded_package(name, desc, config):
    package = f"name={name},description={desc},system=false"
    if "excludedPackages" in config and package in config["excludedPackages"]:
        config["excludedPackages"].remove(package)
    return config

def get_config_section(section, config):
    return config.get(section, {})

def update_dotnet_config(appd_controller_url, bearer, app_id, app_config, verb):
    dotnet_config = get_config_section("dotNetCallGraphConfiguration", app_config)
    if verb == "add":
        dotnet_config = add_excluded_package(PACKAGE, DESCRIPTION, dotnet_config)
    elif verb == "remove":
        dotnet_config = remove_excluded_package(PACKAGE, DESCRIPTION, dotnet_config)
    save_app_configuration(appd_controller_url, bearer, app_id, "DOT_NET_APP_AGENT", dotnet_config)

def update_callgraph_config(appd_controller_url, bearer, app_id, app_config, verb):
    callgraph_config = get_config_section("callGraphConfiguration", app_config)
    if verb == "add":
        callgraph_config = add_excluded_package(PACKAGE, DESCRIPTION, callgraph_config)
    elif verb == "remove":
        callgraph_config = remove_excluded_package(PACKAGE, DESCRIPTION, callgraph_config)
    save_app_configuration(appd_controller_url, bearer, app_id, "APP_AGENT", callgraph_config)

def update_application_config(appd_controller_url, bearer, app_name, verb, agent_type):
    app_id = get_application_id(appd_controller_url, bearer, app_name)
    app_config = get_app_configuration(appd_controller_url, bearer, app_id)

    if agent_type in ["both", "dotnet"]:
        update_dotnet_config(appd_controller_url, bearer, app_id, app_config, verb)
    if agent_type in ["both", "java"]:
        update_callgraph_config(appd_controller_url, bearer, app_id, app_config, verb)

def get_all_applications(appd_controller_url, bearer):
    response = requests.get(
        f"{appd_controller_url}controller/rest/applications?output=JSON",
        headers={"Authorization": f"Bearer {bearer}"}
    )
    response.raise_for_status()
    return [app["name"] for app in response.json()]

def update_all_applications(appd_controller_url, bearer, verb, agent_type):
    applications = get_all_applications(appd_controller_url, bearer)
    for app in applications:
        print(f"Running for \"{app}\"")
        update_application_config(appd_controller_url, bearer, app, verb, agent_type)

def load_application_list(file_path):
    if not os.path.exists(file_path):
        print(f"Application file {file_path} does not exist")
        exit(1)
    with open(file_path) as f:
        applications = [line.strip() for line in f if line.strip()]
    return applications

def main():
    parser = argparse.ArgumentParser(description="AppDynamics Configuration Script")
    parser.add_argument("-a", "--application", required=True, help="Application Name|ALL|file containing application names")
    parser.add_argument("-c", "--config", default="appdynamics-configuration.sh", help="Config file")
    parser.add_argument("-v", "--verb", choices=["add", "remove"], default="add", help="Action to perform: add or remove")
    parser.add_argument("-t", "--agent_type", choices=["java", "dotnet", "both"], default="both", help="Agent type to update: java, dotnet, or both")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if args.debug:
        import logging
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

    if args.application == "ALL":
        confirmation = input(f"Please confirm with a 'YES' if you intended to run this for all applications on the controller {appd_controller_url}: ")
        if confirmation == "YES":
            print("Confirmed")
            update_all_applications(appd_controller_url, bearer, args.verb, args.agent_type)
        else:
            print("That was not a confirmation, so exiting")
            exit(1)
    else:
        if os.path.isfile(args.application):
            applications = load_application_list(args.application)
            for app in applications:
                update_application_config(appd_controller_url, bearer, app, args.verb, args.agent_type)
        else:
            update_application_config(appd_controller_url, bearer, args.application, args.verb, args.agent_type)

if __name__ == "__main__":
    main()
