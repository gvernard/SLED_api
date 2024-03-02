import os
import time
import slack_sdk
from slack_sdk.errors import SlackApiError



def get_slack_avatar(slack_name_avatar):
    '''
    Takes as input a list of dicts with {"slack_display_name":, "avatar":}.
    The code fetches the avatar information through the Slack API and checks if the avatar has changed.
    If yes, then the "avatar" field is updated.

    The function outputs:
    1. the updated input list,
    2. a list of boolean flags to show which list items have been updated
    3. a list of errors.
    '''
    SLACK_TOKEN = os.environ['DJANGO_SLACK_API_TOKEN']
    slack_client = slack_sdk.WebClient(SLACK_TOKEN)

    looper = True
    counter = 1
    errors = []
    flags = [False]*len(slack_name_avatar)
    while looper and counter < 10:
        try:
            response = slack_client.users_list()
        except SlackApiError as e:
            if e.response["error"] == "ratelimited":
                print("Retrying connection to Slack API...")
                time.sleep(3)
                counter = counter + 1
            else:
                # Other error
                errors.append( ("__all__","Slack API error: " + e.response["error"]) )
                looper = False
                pass
        else:
            if response["ok"]:
                #print(response["members"])
                for i in range(0,len(slack_name_avatar)):
                    in_name = slack_name_avatar[i]["slack_name"]
                    in_avatar = slack_name_avatar[i]["avatar"]

                    found = False
                    for j in range(0,len(response["members"])):
                        slack_name = response["members"][j]["profile"]["display_name"]
                        slack_avatar = response["members"][j]["profile"]["image_512"]
                        if in_name == slack_name:
                            if in_avatar != slack_avatar:
                                slack_name_avatar[i]["avatar"] = slack_avatar
                                flags[i] = True
                            found = True
                            break

                    if not found:
                        errors.append( ("__all__","User '" + in_name + "' does not exist in the SLED Slack workspace!") )

            looper = False

                                
        if counter >= 10:
            errors.append( ("__all__","Too many requests to the Slack API. Please try again later!") )

    return errors,flags,slack_name_avatar
