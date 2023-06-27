#!/bin/bash

#AGENT_TYPE="DOT_NET_APP_AGENT"
#NEW_NODE_PROPERTY='{"definition":{"type":"BOOLEAN","allowedStringValues":null,"defaultFileBinary":null,"defaultStringValue":null,"description":"agentless-analytics-disabled description","lowerNumericBound":null,"name":"agentless-analytics-disabled","required":false,"stringMaxLen":0,"upperNumericBound":null,"id":0,"version":0},"fileBinary":null,"stringValue":"false","id":0,"version":0}'

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
    t)
      TIER_NAME="$OPTARG"
      ;;
    d)
      set -x
      ;;
    p)
      PROPERTY_FILE="$OPTARG"
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
  echo "usage: $0 -p \"PROPERTY FILE\" -a \"Application Name|ALL\" [ -t \"Tier Name|ALL|NONE\" ] [ -c \"config_file\" ] [ -d ] "
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

if [ -f "$PROPERTY_FILE" ]; then
  . $PROPERTY_FILE
  if [ -z "$AGENT_TYPE" ] || [ -z "$NEW_NODE_PROPERTY" ]; then
    echo "Property file does not set AGENT_TYPE and/or NEW_NODE_PROPERTY"
    exit 1
  fi
else
  echo "PROPERTY_FILE needs to be set with valid node property to add"
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

function getApplicationTierID() {
  local appId=$1
  local tierName=$2

  local response=$( curl -s "${APPD_CONTROLLER_URL}controller/rest/applications/${appId}/?output=JSON" -H "Authorization: Bearer $BEARER" )
  echo $(echo $response | jq --arg n "$tierName" '.[] | select( .name == $n ).id' )
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

function getAppTierNodeProperties() {
  local appName=$1
  local tierName=$2

  local appId=$( getApplicationID "$appName")
  local tierId=$( getApplicationTierID "$appId" "$tierName")
  local response=$(curl -s -H "Authorization: Bearer $BEARER" \
    -H 'Content-Type: application/json;charset=UTF-8' \
    -H 'Accept: application/json, text/plain, */*' \
    "${APPD_CONTROLLER_URL}controller/restui/agentManager/getAgentConfiguration" -d "{\"checkAncestors\":false,\"key\":{\"agentType\":\"${AGENT_TYPE}\",\"attachedEntity\":{\"id\":null,\"version\":null,\"entityId\":${appId},\"entityType\":\"APPLICATION_COMPONENT\"}}}" )
    echo $response
}

function setNodeProperties() {
  local DATA=$( echo "$1" )
  local response=$(curl -s  -H "Authorization: Bearer $BEARER" \
    -H 'Content-Type: application/json;charset=UTF-8' \
    -H 'Accept: application/json, text/plain, */*' \
    "${APPD_CONTROLLER_URL}controller/restui/agentManager/updateAgentConfigurationAndToggleAgentEnableStatusIfNeeded" -d "$DATA" )
    echo $response
}

function updateApplicationNodeProperty() {
  local application=$(echo $1)
  local nodeProperty=$( echo $2)
  local configurationData=$(getAppNodeProperties "$application")
  updateConfigurationData=$(echo "$configurationData" | jq -c --argjson element "$nodeProperty" '.properties += [$element]' )
  echo $(setAppNodeProperties "$updateConfigurationData")
}

function updateTierNodeProperty() {
  local application=$(echo $1)
  local tier=$(echo $2)
  local nodeProperty=$( echo $3)
  local configurationData=$(getAppTierNodeProperties "$application" "$tier")
  updateConfigurationData=$(echo "$configurationData" | jq -c --argjson element "$nodeProperty" '.properties += [$element]' )
  echo $(setNodeProperties "$updateConfigurationData")
}

function getCustomizedTiersForApplication () {
  local appId=$( getApplicationID "$1" )
  local response=$(curl -s  -H "Authorization: Bearer $BEARER" \
                       -H 'Content-Type: application/json;charset=UTF-8' \
                       -H 'Accept: application/json, text/plain, */*' \
                       "${APPD_CONTROLLER_URL}controller/restui/agentManager/getAllApplicationComponentsWithNodes/${appId}")
  echo $(echo $response | jq --arg agentType "$AGENT_TYPE" '.[].children[] | select(.agentType == $agentType and .customized == true) | .agentConfigId' )
}

function updateAllApplicationsAllTiers() {
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
      for tierId in $( getCustomizedTiersForApplication "$application" ); do
        echo "Running for \"$application\" tier id: \"$tierId\""
        updateTierNodeProperty "$application" "$tierId" "$NEW_NODE_PROPERTY"
      done
    fi
  done
}

function updateApplicationAllTiers() {
  local application=$1
  local new_node_properties=$2

  for tierId in $( getCustomizedTiersForApplication "$application" ); do
    echo "Running for \"$application\" tier id: \"$tierId\""
    updateTierNodeProperty "$application" "$tierId" "$new_node_properties"
  done
}

BEARER=$(getBearerToken)
if [ "$APPLICATION_NAME" == "ALL" ]; then
  echo "Please confirm with a 'YES' if you intended to run this for all applications on the controller $APPD_CONTROLLER_URL"
  read confirmation
  if [ "$confirmation" == "YES" ]; then
    echo Confirmed
    if [ "$TIER_NAME" == "NONE" ]; then
      echo $(updateAllApplications)
    elif [ "$TIER_NAME" == "ALL" ]; then
      echo $(updateAllApplicationsAllTiers)
    else
      echo "We don't support the option of all applications and one specific tier, don't try this again"
      exit 1
    fi
  else
    echo "that was not a confirmation, so exiting"
    exit
  fi
else
  if [ "$TIER_NAME" == "NONE" ]; then
    updateApplicationNodeProperty "$APPLICATION_NAME" "$NEW_NODE_PROPERTY"
  elif [ "$TIER_NAME" == "ALL" ]; then
    updateApplicationAllTiers "$APPLICATION_NAME" "$NEW_NODE_PROPERTY"
  else
    updateTierNodeProperty "$APPLICATION_NAME" "$TIER_NAME" "$NEW_NODE_PROPERTY"
  fi
fi