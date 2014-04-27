import json
from time import sleep
from random import randint

from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.utils import IntegrityError

from game.models import Match, PlayerInGame, Step
from game.steps import resolve

# Create your views here.
@ensure_csrf_cookie
def game_view(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    home_players = PlayerInGame.objects.filter(
        match=match, player__team=match.home_team).all()
    away_players = PlayerInGame.objects.filter(
        match=match, player__team=match.away_team).all()
    players_list = []
    players_list.extend([p.as_dict('home') for p in home_players])
    players_list.extend([p.as_dict('away') for p in away_players])
    players_json = json.dumps(players_list)
    history = Step.objects.filter(match=match).order_by('history_position')
    history = json.dumps([a.as_dict() for a in history])
    data = {
        'players_json': players_json,
        'match_data': json.dumps(match.as_dict()),
        'history': history,
    }
    return render(request, 'game/game.html', data)

def post_step_view(request):
    # sleep(randint(1, 5))
    # Get the match in question
    print('post_step_view')
    print('POST:', request.POST)
    match = Match.objects.get(id=request.POST['matchId'])
    # Check what steps have previously been saved
    history_saved = Step.objects.filter(match=match).values_list(
        'history_position', flat=True).order_by('history_position')
    if len(history_saved) == 0:
        expected_position = 0
    else:
        expected_position = history_saved[len(history_saved)-1] + 1
    # Check where this new step fits in with the history
    history_position = int(request.POST['historyPosition'])
    print('expected:', expected_position, 'actual:', history_position)
    if history_position > expected_position:
        # Missing some history, so request it be resent
        result = {'status': 'resend',
                  'start': expected_position}
    elif history_position < expected_position:
        # Already have this one
        # Should also check against the database for consistency
        result = {'status': 'duplicate'}
    else:
        # This is the next step, as expected
        # Turn the POST data into a model step
        properties = {key: value for key, value in request.POST.items() 
                      if key not in ['stepType', 'matchId', 'historyPosition']}
        print(str(history_position) + ':', properties)
        step_type = request.POST['stepType']
        step = Step(
            step_type=step_type,
            match=match,
            history_position=history_position,
            properties=json.dumps(properties))
        try:
            step.save()
        except IntegrityError:
            # A conflicting step exists in the database
            result = {'status': 'duplicate'}
        else:
            # Carry out the step
            print(str(history_position) + ':', "Carrying out the step")
            try:
                result = resolve(match, step_type, properties)
            except Exception as e:
                print(e)
                raise
            # Add the result to the step in the database
            step.result = json.dumps(result)
            step.save()
            # Tell the client that everything is ok
            result['status'] = 0
    result_json = json.dumps(result)
    print(str(history_position) + ':', result_json)
    return HttpResponse(result_json, content_type="application/json")
