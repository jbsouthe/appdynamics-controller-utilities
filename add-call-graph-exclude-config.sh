#!/bin/bash

PACKAGE="com.john"
DESCRIPTION="test for john"

#####################################################################
##### Don't modify this stuff below unless you can fix it ###########
#####################################################################

if ! command -v jq &>/dev/null; then
    echo "Error: 'jq' is not installed. Please install 'jq' to proceed."
    exit 1
fi

CONFIG_FILE="appdynamics-configuration.sh"
TIER_NAME="NONE"

# Parse command line arguments
while getopts "c:a:t:dp:" opt; do
  case $opt in
    c)
      CONFIG_FILE="$OPTARG"
      ;;
    a)
      APPLICATION_NAME="$OPTARG"
      ;;
    d)
      set -x
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

if [ -z "$APPLICATION_NAME" ]; then
  echo "usage: $0 -a \"Application Name\" [ -c \"config_file\" ] [ -d ] "
  exit 1
fi

if [ -f "$CONFIG_FILE" ]; then
  . $CONFIG_FILE
  if [ -z $APPD_CONTROLLER_URL ] || [ -z $APPD_CLIENT_ID ] || [ -z $APPD_CLIENT_SECRET ]; then
    echo "could not load AppDynamics Configuration from $CONFIG_FILE, please set that up or something"
    exit 1
  fi
else
  echo "Config file $CONFIG_FILE does not exist"
  exit 1
fi

function getBearerToken() {
    local APPD_ACCOUNT=$(echo $APPD_CONTROLLER_URL | awk -F[/:.] '{print $4}')
    #get an AppDynamics token response
    local appd_token_response=$(curl -s -X POST -H "Content-Type: application/x-www-form-urlencoded" -u "$APPD_CLIENT_ID:$APPD_CLIENT_SECRET" "${APPD_CONTROLLER_URL}controller/api/oauth/access_token" -d "grant_type=client_credentials&client_id=${APPD_CLIENT_ID}@${APPD_ACCOUNT}&client_secret=${APPD_CLIENT_SECRET}")

    #grab the bearer token part
    local appd_access_token=$(echo "$appd_token_response" | awk -F'"' '{print $4}' )
    echo $appd_access_token
}

function getApplicationID() {
  local appname=$1

  local response=$( curl -s "${APPD_CONTROLLER_URL}controller/rest/applications?output=JSON" -H "Authorization: Bearer $BEARER" )
  echo $(echo $response | jq --arg n "$appname" '.[] | select( .name == $n ).id' )
}

function getAppConfiguration() {
  local appId=$1

  local response=$(curl -s -H "Authorization: Bearer $BEARER" \
    -H 'Content-Type: application/json;charset=UTF-8' \
    -H 'Accept: application/json, text/plain, */*' \
    "${APPD_CONTROLLER_URL}controller/restui/applicationManagerUiBean/applicationConfiguration/${appId}" )
    echo $response
}

function saveAppConfiguration() {
  local appId=$1
  local agentType=$2
  local config=$3

  local response=$(curl -s -H "Authorization: Bearer $BEARER" \
	-H 'Content-Type: application/json;charset=UTF-8' \
	-H 'Accept: application/json, text/plain, */*' \
    "${APPD_CONTROLLER_URL}controller/restui/configuration/callGraph/save" \
	--data-raw "{\"agentType\":\"$agentType\",\"applicationId\":$appId,\"config\":$config}" )
    echo $response
}

function addExcludedPackage() {
  local name=$1
  local desc=$2
  local config=$3
  local package="\"name="$name",description="$desc",system=false\""
  echo ${config} | jq -c --argjson newPkg "$package" \
   'if .excludedPackages | index($newPkg) then . else .excludedPackages += [$newPkg] end'
}

function getConfigSection() {
  local section=$1
  local config=$2
  echo ${config} | jq --arg section "$section" '.[$section]'
}  

BEARER=$(getBearerToken)
APP_ID=$( getApplicationID "$APPLICATION_NAME")
APP_CONFIG=$(getAppConfiguration $APP_ID)

config=$( getConfigSection "dotNetCallGraphConfiguration" "$APP_CONFIG" )
config=$( addExcludedPackage "$PACKAGE" "$DESCRIPTION" "$config" )
saveAppConfiguration $APP_ID "DOT_NET_APP_AGENT" "$config"

config=$( getConfigSection "callGraphConfiguration" "$APP_CONFIG" )
config=$( addExcludedPackage "$PACKAGE" "$DESCRIPTION" "$config" )
saveAppConfiguration $APP_ID "APP_AGENT" "$config"
