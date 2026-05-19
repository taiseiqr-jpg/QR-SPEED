from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.views.decorators.csrf import csrf_protect

def home(request):
    return HttpResponse("Blank")


def test(request):
  template = loader.get_template('test.html')
  return HttpResponse(template.render())

@csrf_protect  # Ensures CSRF protection is applied to this view
def worker(request):
    # Render the form for creating a worker
    return render(request, 'employee_info.html')

def product_create(request):
    # Render the form for creating a product
    return render(request, 'product_create.html')

def output(request):
    # Render the form for creating worker output
    return render(request, 'output.html')

def product_update(request):
    # Render the form for updating product
    return render(request, 'product_update.html')

def output_register(request):
    # Render the form for updating product
    return render(request, 'output_register.html')

def login(request):
    # Render the form for updating product
    return render(request, 'login.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def customer_create(request):
    return render(request, 'customer_create.html')

def item_add(request):
    return render(request, 'item_create.html')

def material_update(request):
    return render(request, 'material_update.html')
