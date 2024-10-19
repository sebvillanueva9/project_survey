
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.cache import never_cache

@login_required
@never_cache
def home(request):
    return render(request, 'procesamiento/home.html')
