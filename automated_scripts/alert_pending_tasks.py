from django.core.mail import send_mail
from django.template.loader import get_template
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.html import strip_tags

from lenses.models import Users, ConfirmationTask



# Fetch all users with pending tasks
#users = Users.objects.filter(confirmationtask__status='P')
users = Users.objects.filter(confirmation_tasks__status='P').distinct()


subject = 'SLED: Response to pending tasks required'
from_email = 'sled-no-reply@sled.amnh.org'
site = Site.objects.get_current()

for user in users:
    html_message = get_template('emails/alert_pending_tasks.html')
    mycontext = {
        'first_name': user.first_name,
        'protocol': 'https',
        'domain': site.domain,
        'task_url': reverse('sled_tasks:tasks-list')
    }
    html_message = html_message.render(mycontext)
    plain_message = strip_tags(html_message)
    recipient_email = user.email
    send_mail(subject,plain_message,from_email,[recipient_email],html_message=html_message)
