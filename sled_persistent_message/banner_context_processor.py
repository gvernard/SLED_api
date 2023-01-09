from lenses.models import PersistentMessage

def current_messages(request):
    return {
        'current_messages': PersistentMessage.timeline.current()
    }
