from django.shortcuts import redirect,render


def admin_test(user):
    if user.limitsandroles.is_admin:
        return True
    return False

def superadmin_test(user):
    if user.limitsandroles.is_superadmin:
        return True
    return False


def admin_access_only(view):

    def decorator(request,*args,**kwargs):
        if not admin_test(request.user):
            return render(request,'404.html',status=404)
        return view(request, *args, **kwargs)
    
    return decorator

