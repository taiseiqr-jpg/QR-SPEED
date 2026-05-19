from django.urls import path
from . import views
from .api import api

urlpatterns = [
    path('home/', views.home, name='home'),
    path('worker/create', views.worker),
    path('product/create', views.product_create),
    path('output/', views.output),
    path('product/update', views.product_update),
    path('output/register', views.output_register),
    path('login/', views.login),
    path('dashboard/', views.dashboard),
    path('customer/create', views.customer_create),
    path('item/add', views.item_add),
    path('material/update', views.material_update),
    path('api/', api.urls)
]