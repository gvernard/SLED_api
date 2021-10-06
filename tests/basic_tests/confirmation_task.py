import os
import sys
import django

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

# -----------------------------------------------------


from lenses.models import Users, ConfirmationTasks

users = Users.objects.all()
sender = users.get(username='Giorgos')
receiver = users.get(username='Fred')
cargo = {"bleg": 1}
task_name = 'test_task'

mytask = ConfirmationTasks.create_task(sender,receiver,task_name,cargo)
mytask.save()
print(mytask.id)
print(mytask.not_heard_from())
