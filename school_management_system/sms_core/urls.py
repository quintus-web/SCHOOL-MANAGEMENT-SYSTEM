# sms_core/urls.py
from django.contrib import admin
from django.urls import path, include
# Import the public website view function straight from the finance views file
from finance.views import public_school_website 
from django.contrib import admin
from django.urls import path, include
from finance.views import public_school_website 
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ◄ ROOT PATH: Your beautiful public landing page loads instantly here now
    path('', public_school_website, name='public_home'),
    
    # Your internal management application ecosystem portals sub-routes
   
    
     path('', include('finance.urls')),
]

# Custom view to catch unauthorized access attempts across the platform
def custom_permission_denied_handler(request, exception=None):
    messages.error(request, "Access Restricted! Your account does not have the necessary clearance level for that workstation.")
    return redirect('public_home')

handler403 = 'sms_core.urls.custom_permission_denied_handler'
