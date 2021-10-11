from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F,Q,Count

import json

import lenses
from lenses.models import Users, ConfirmationTask


@login_required
def list_tasks(request):
    tasks = ConfirmationTask.objects.filter(owner__username=request.user.username)
    receivers = []
    for task in tasks:
        names = list(task.get_all_receivers().values_list('username',flat=True))
        receivers.append(','.join(names))
    list1 = zip(receivers,tasks)
    N_list1 = len(tasks)
    
    tasks = ConfirmationTask.objects.annotate(num_receivers=Count('receivers')).filter(receivers__username=request.user.username).filter(num_receivers__exact=1)
    receivers = []
    for task in tasks:
        names = list(task.get_all_receivers().values_list('username',flat=True))
        receivers.append(','.join(names))    
    list2 =  zip(receivers,tasks)
    N_list2 = len(tasks)

    tasks = ConfirmationTask.objects.annotate(num_receivers=Count('receivers')).filter(receivers__username=request.user.username).filter(num_receivers__gt=1)
    receivers = []
    for task in tasks:
        names = list(task.get_all_receivers().values_list('username',flat=True))
        receivers.append(','.join(names))
    list3 =  zip(receivers,tasks)
    N_list3 = len(tasks)

    return render(request,'confirmation_task_list.html',context={'list1':list1,'N_list1':N_list1,'list2':list2,'N_list2':N_list2,'list3':list3,'N_list3':N_list3})
    

@login_required
def single_task(request,task_id):
    task = ConfirmationTask.load_task(task_id)

    if not task:
        # Task does not exist
        html = "<html><body>There is no such task!</body></html>"
        return HttpResponse(html)
    
    elif request.user.username == task.owner.username:
        # User is the owner
        allowed = ' or '.join(task.get_allowed_responses())
        hf = task.heard_from().annotate(name=F('receiver__username')).values('name','response','created_at','response_comment')
        nhf = task.not_heard_from().values_list('receiver__username',flat=True)
        return render(request,'confirmation_task_single.html',context={'task':task,'owned':True,'allowed':allowed,'hf':hf,'nhf':nhf})

    elif request.user.username in task.receiver_names:
        # User is a receiver
        form = task.getForm()
        # create objects from cargo
        object_type = task.cargo["object_type"]
        object_ids = task.cargo['object_ids']
        objects = getattr(lenses.models,object_type).objects.filter(pk__in=object_ids)
        link_list = []
        for i,obj in enumerate(objects):
            link_list.append({'name':obj.name,'link':obj.getLink()})
        comment = ''
        if "comment" in task.cargo:
            comment = task.cargo["comment"]

        # Get user response from the database
        db_response = task.receivers.through.objects.get(confirmation_task__exact=task.id,receiver__username=request.user.username)
    
        if not db_response.response:
            # Response does not exist in the database, render an editable form
            if request.POST:
                response = request.POST.get('response')
                response_comment = request.POST.get('response_comment')
                task.registerAndCheck(request.user,response,response_comment)
                db_response = task.receivers.through.objects.get(confirmation_task__exact=task.id,receiver__username=request.user.username)

                form.fields["response"].initial = db_response.response
                form.fields["response"].disabled = True
                if db_response.response_comment:
                    form.fields["response_comment"].initial = db_response.response_comment
                    form.fields["response_comment"].disabled = True
        else:
            # Response ALREADY in the database, render a disabled form
            form.fields["response"].initial = db_response.response
            form.fields["response"].disabled = True
            if db_response.response_comment:
                form.fields["response_comment"].initial = db_response.response_comment
                form.fields["response_comment"].disabled = True

        return render(request,'confirmation_task_single.html',context={'task':task,'owned':False,'form':form,'object_type':object_type,'links':link_list,'comment':comment,'db_response':db_response})

    else:
        # User shouldn't be allowed to access this task
        html = "<html><body>You are not involved in this task!</body></html>"
        return HttpResponse(html)


        
    


