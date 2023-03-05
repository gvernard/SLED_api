import os
import sys
import django
dirname = os.path.dirname(__file__)
sys.path.append(dirname)
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users
from sled_core.slack_api_calls import get_slack_avatar


users = Users.objects.all()
slack_name_avatar = []
users_in_slack = []
for u in users:
    if u.slack_display_name:
        users_in_slack.append( u )
        slack_name_avatar.append( {"slack_name":u.slack_display_name,"avatar":u.avatar} )



if len(slack_name_avatar) > 0:
    errors,flags,slack_name_avatar = get_slack_avatar(slack_name_avatar)

    if errors:
        for e in errors:
            print(e[0],e[1])  
        print("No user avatars where updated")
    else:
        counter = 0
        for i in range(0,len(slack_name_avatar)):
            if flags[i]:
                users_in_slack[i].avatar = slack_name_avatar[i]["avatar"]
                users_in_slack[i].save(update_fields=['avatar'])
                print(users_in_slack[i]," 's avatar was updated")
                counter = counter + 1
        if counter == 0:
            print("No user avatars where updated")

else:
    print("None of the users has setup their slack name.")
