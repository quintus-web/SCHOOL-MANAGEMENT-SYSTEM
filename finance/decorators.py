# finance/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

def group_required(group_name):
    """
    Decorator for views that checks whether a user belongs to a specific security group.
    Redirects with a warning message if they do not have authorization.
    """
    def in_group(user):
        if user.is_authenticated:
            # Superusers bypass all restrictions automatically
            if user.is_superuser or user.groups.filter(name=group_name).exists():
                return True
            raise PermissionDenied
        return False
        
    return user_passes_test(in_group)
