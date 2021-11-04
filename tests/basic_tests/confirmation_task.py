import os
import sys
import json
import django
from django.db.models import Q

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

# -----------------------------------------------------


from lenses.models import Users, ConfirmationTask

users = Users.objects.all()

# (This block should be replaced by a call to cedeownership)
# Send from Giorgos to Fred, pending
sender = users.get(username='gvernard')
receivers = users.filter(username='Fred')
task_type = 'CedeOwnership'
cargo = {"object_type": "Lenses",
         "object_ids":[1,2,3],
         "comment": "Can you please take ownership of these lenses?"
         }
mytask = ConfirmationTask.create_task(sender,receivers,task_type,cargo)


# (This block should be replaced by a call to cedeownership)
# Send from Giorgos to Fred, complete
sender = users.get(username='gvernard')
receivers = users.filter(username='Fred')
task_type = 'CedeOwnership'
cargo = {"object_type": "Lenses",
        "object_ids": [4],
        "comment": "Oops, I forgot to add one more :)"
        }
mytask = ConfirmationTask.create_task(sender,receivers,task_type,cargo)


target_receiver = users.get(username='Fred')
mytask.registerAndCheck(target_receiver,'yes','I will happily take over.')






# (This block should be replaced by a call to cedeownership)
# Send from Fred to Giorgos, pending
sender = users.get(username='Fred')
receivers = users.filter(username='gvernard')
task_type = 'CedeOwnership'
cargo = {"object_type": "Lenses",
         "object_ids":[10],
         "comment": ""
         }
mytask = ConfirmationTask.create_task(sender,receivers,task_type,cargo)


# (This block should be replaced by a call to cedeownership)
# Send from Cameron to Giorgos, pending
sender = users.get(username='Cameron')
receivers = users.filter(username='gvernard')
task_type = 'CedeOwnership'
cargo = {"object_type": "Lenses",
         "object_ids":[50],
         "comment": "Can you own this lens?"
         }
mytask = ConfirmationTask.create_task(sender,receivers,task_type,cargo)




# (This block should be replaced by a call to cedeownership)
# Send from Cameron to Giorgos and Fred, pending
sender = users.get(username='Cameron')
receivers = users.filter(Q(username='gvernard')|Q(username='Fred'))
task_type = 'CedeOwnership'
cargo = {"object_type": "Lenses",
         "object_ids":[50],
         "comment": "This is a dummy task that is sent to 2 users."
         }
mytask = ConfirmationTask.create_task(sender,receivers,task_type,cargo)


'''
sender = users.get(username='Fred')
receivers = users.filter(username='Cameron')
#receivers = list(users.exclude(username__in=['admin','AnonymousUser']))
cargo = {"seed": 123}
task_type = 'MakePrivate'
print("Given receivers are: ",receivers)
mytask = ConfirmationTask.create_task(sender,receivers,task_type,cargo)
print("Receivers in DB are: ",mytask.get_all_receivers())

print(mytask._receiver_names)
target_receiver = users.get(username='Cameron')
mytask.registerAndCheck(target_receiver,'yes')
print(mytask.get_allowed_responses())
'''



# mytask = ConfirmationTask.create_task(sender,receivers,task_name,cargo)

# print()
# print(mytask.get_all_receivers())
# print()
# nhf = mytask.not_heard_from()
# print(nhf.values('receiver__username','response'))
# hf = mytask.heard_from()
# print(hf.values('receiver__username','response'))
# print()


# target_receiver = users.get(username='Fred')
# mytask.registerResponse(target_receiver,'no')
# target_receiver = users.get(username='Giorgos')
# mytask.registerResponse(target_receiver,'maybe')

# print()
# nhf = mytask.not_heard_from()
# print(nhf.values('receiver__username','response'))
# hf = mytask.heard_from()
# print(hf.values('receiver__username','response'))
# print()



