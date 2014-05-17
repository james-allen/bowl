from django.contrib.auth import logout
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q

from game.models import Match


def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')

@login_required
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    this_user = (request.user.username == username)
    match_set = Match.objects.filter(
        Q(home_team__coach=user) |
        Q(away_team__coach=user)
        )
    data = {'username': username,
            'user': user,
            'this_user': this_user,
            'match_set': match_set,
            }
    return render(request, 'profile.html', data)
