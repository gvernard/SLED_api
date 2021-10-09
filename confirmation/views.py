from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F,Q,Count

from lenses.models import Users, ConfirmationTask

@login_required
def index(request):
    tasks = ConfirmationTask.objects.filter(owner__username=request.user.username)
    receivers = []
    for task in tasks:
        names = list(task.get_all_receivers().values_list('username',flat=True))
        receivers.append(','.join(names))
    mylist1 = zip(receivers,tasks)


    tasks = ConfirmationTask.objects.annotate(num_receivers=Count('receivers')).filter(receivers__username=request.user.username).filter(num_receivers__exact=1)
    receivers = []
    for task in tasks:
        names = list(task.get_all_receivers().values_list('username',flat=True))
        receivers.append(','.join(names))    
    mylist2 =  zip(receivers,tasks)


    tasks = ConfirmationTask.objects.annotate(num_receivers=Count('receivers')).filter(receivers__username=request.user.username).filter(num_receivers__gt=1)
    receivers = []
    for task in tasks:
        names = list(task.get_all_receivers().values_list('username',flat=True))
        receivers.append(','.join(names))
    mylist3 =  zip(receivers,tasks)

    return render(request,'all_tasks.html',context={'by_me':mylist1,'to_me':mylist2,'not_just_to_me':mylist3})
    

@login_required
def task_to_confirm(request,task_id):
    task = ConfirmationTask.load_task(task_id)

    if request.user.username not in task.receiver_names:
        html = "<html><body>You are not a receiver of this task!</body></html>"
        return HttpResponse(html)


    form = task.getForm()
    # create objects from cargo
    object_type = task.cargo["object_type"]
    objects = []
    for i in range(0,len(task.cargo['object_ids'])):
        objects.append({'name':'Lens_'+str(task.cargo['object_ids'][i]),'link':'https://gerlumph.swin.edu.au'})
    comment = task.cargo["comment"]

    
    # Get user response from the database
    db_response = task.receivers.through.objects.get(confirmation_task__exact=task.id,receiver__username=request.user.username)
    
    if not db_response.response:
        # Response does not exist in the database, render an editable form
        if request.POST:
            response = request.POST.get('response')
            comment = request.POST.get('response_comment')
            task.registerAndCheck(request.user,response,comment)
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

    
    return render(request,'task_to_confirm.html',context={'task':task,'form':form,'object_type':object_type,'objects':objects,'comment':comment,'db_response':db_response})


@login_required
def owned_task(request,task_id):
    task = ConfirmationTask.load_task(task_id)
    if request.user.username != task.owner.username:
        html = "<html><body>You are not the owner of this task!</body></html>"
        return HttpResponse(html)

    allowed = ' or '.join(task.get_allowed_responses())
    hf = task.heard_from().annotate(name=F('receiver__username')).values('name','response','created_at','response_comment')
    nhf = task.not_heard_from().values_list('receiver__username',flat=True)
    #check if indeed owned by the user
    
    return render(request,'owned_task.html',context={'task':task,'allowed':allowed,'hf':hf,'nhf':nhf})
