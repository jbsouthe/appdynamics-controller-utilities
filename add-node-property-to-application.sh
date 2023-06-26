#!/bin/bash

#################### Configure this stuff ############################

AGENT_TYPE="DOT_NET_APP_AGENT"
NEW_NODE_PROPERTY='{"definition":{"type":"BOOLEAN","allowedStringValues":null,"defaultFileBinary":null,"defaultStringValue":null,"description":"agentless-analytics-disabled description","lowerNumericBound":null,"name":"agentless-analytics-disabled","required":false,"stringMaxLen":0,"upperNumericBound":null,"id":0,"version":0},"fileBinary":null,"stringValue":"false","id":0,"version":0}'

#Some AppDynamics configuration:
. appdynamics-configuration.sh

#####################################################################
##### Don't modify this stuff below unless you can fix it ###########
#####################################################################
if [ -z $APPD_CONTROLLER_URL ] || [ -z $APPD_CLIENT_ID ] || [ -z $APPD_CLIENT_SECRET ]; then
  echo "could not load AppDynamics Configuration from appdynamics-configuration.sh, please set that up or something"
  exit 1
fi

if ! command -v jq &>/dev/null; then
    echo "Error: 'jq' is not installed. Please install 'jq' to proceed."
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



function getAllApplications() {
  local response=$( curl -s "${APPD_CONTROLLER_URL}controller/rest/applications?output=JSON" -H "Authorization: Bearer $BEARER" )
  echo $(echo $response | jq '.[].name' )
}

function updateAllApplications() {
  local input=$(getAllApplications)
  input=${input#\"}
  input=${input%\"}

  # Split the input into individual quoted strings
  IFS='"' read -ra strings <<< "$input"

  # Iterate over the strings and print each one
  for application in "${strings[@]}"; do
    if [ "$application" != " " ]; then
      echo "Running for \"$application\""
      updateNodeProperty "$application" "$NEW_NODE_PROPERTY"
    fi
  done
}

function getApplicationID() {
  local appname=$1

  local response=$( curl -s "${APPD_CONTROLLER_URL}controller/rest/applications?output=JSON" -H "Authorization: Bearer $BEARER" )
  echo $(echo $response | jq --arg n "$appname" '.[] | select( .name == $n ).id' )
}

function getAppNodeProperties() {
  local appName=$1

  local appId=$( getApplicationID "$appName")
  local response=$(curl -s -H "Authorization: Bearer $BEARER" \
    -H 'Content-Type: application/json;charset=UTF-8' \
    -H 'Accept: application/json, text/plain, */*' \
    "${APPD_CONTROLLER_URL}controller/restui/agentManager/getAgentConfiguration" -d "{\"checkAncestors\":false,\"key\":{\"agentType\":\"${AGENT_TYPE}\",\"attachedEntity\":{\"id\":null,\"version\":null,\"entityId\":${appId},\"entityType\":\"APPLICATION\"}}}" )
    echo $response
}

function setAppNodeProperties() {
  local DATA=$( echo "$1" )
  local response=$(curl -s  -H "Authorization: Bearer $BEARER" \
    -H 'Content-Type: application/json;charset=UTF-8' \
    -H 'Accept: application/json, text/plain, */*' \
    "${APPD_CONTROLLER_URL}controller/restui/agentManager/updateAgentConfigurationAndToggleAgentEnableStatusIfNeeded" -d "$DATA" )
    echo $response
}

function updateNodeProperty() {
  local application=$(echo $1)
  local nodeProperty=$( echo $2)
  local configurationData=$(getAppNodeProperties "$application")
  updateConfigurationData=$(echo "$configurationData" | jq -c --argjson element "$nodeProperty" '.properties += [$element]' )
  echo $(setAppNodeProperties "$updateConfigurationData")
}

APPLICATION_NAME="$*"
if [ -z "$APPLICATION_NAME" ]; then
  echo "usage: $0 \"Application Name\" | \"ALL\""
  exit 1
fi
BEARER=$(getBearerToken)
if [ "$APPLICATION_NAME" == "ALL" ]; then
  echo "Please confirm with a 'YES' if you intended to run this for all applications on the controller $APPD_CONTROLLER_URL"
  read confirmation
  if [ "$confirmation" == "YES" ]; then
    echo Confirmed
    echo $(updateAllApplications)
  else
    echo "that was not a confirmation, so exiting"
    exit
  fi
else
  updateNodeProperty "$APPLICATION_NAME" "$NEW_NODE_PROPERTY"
fi