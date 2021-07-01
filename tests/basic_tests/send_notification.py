import django

base_dir = '../../'
sys.path.append(base_dir)

from lenses.models import Users, SledGroups, Lenses
from notifications.signals import notify


notify.send(user, recipient=user, verb='you reached level 10')
