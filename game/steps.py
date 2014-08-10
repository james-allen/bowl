from game.models import PlayerInGame, Step, set_kickoff

import random

def finish_previous_action(match, current_player):
    active_steps = ['move', 'block', 'standUp', 'pass', 'foul', 'handOff']
    step_set = Step.objects.filter(match=match).order_by('-history_position')
    for step in step_set:
        if step is step_set[0]:
            continue
        if step.step_type == 'endTurn':
            return
        if step.step_type in active_steps:
            player = find_player(match, step.as_dict())
            if (player.side == current_player.side and 
                    player.player.number == current_player.player.number):
                continue
            player.finished_action = True
            player.save()

def set_action(player, action):
    player.action = action
    player.save()
    finish_previous_action(player.match, player)

def n_tackle_zones(player):
    opponents = PlayerInGame.objects.filter(
        match=player.match)
    opponents = opponents.exclude(
        player__team=player.player.team)
    opponents = opponents.filter(
        xpos__gt=(player.xpos-2), ypos__gt=(player.ypos-2))
    opponents = opponents.filter(
        xpos__lt=(player.xpos+2), ypos__lt=(player.ypos+2))
    opponents = opponents.filter(
        tackle_zones=True)
    opponents = opponents.filter(
        on_pitch=True)
    return opponents.count()

def find_pass_range(delta_x, delta_y):
    if ((delta_x <= 1 and delta_y <= 3) or
        (delta_x == 2 and delta_y <= 2) or
        (delta_x == 3 and delta_y <= 1)):
        return 'quickPass'
    elif ((delta_x <= 3 and delta_y <= 6) or
          (delta_x == 4 and delta_y <= 5) or
          (delta_x == 5 and delta_y <= 4) or
          (delta_x == 6 and delta_y <= 3)):
        return 'shortPass'
    elif ((delta_x <= 2 and delta_y <= 10) or
          (delta_x <= 4 and delta_y <= 9) or
          (delta_x <= 6 and delta_y <= 8) or
          (delta_x == 7 and delta_y <= 7) or
          (delta_x == 8 and delta_y <= 6) or
          (delta_x == 9 and delta_y <= 4) or
          (delta_x == 10 and delta_y <= 2)):
        return 'longPass'
    elif ((delta_x <= 1 and delta_y <= 13) or
          (delta_x <= 4 and delta_y <= 12) or
          (delta_x <= 6 and delta_y <= 11) or
          (delta_x <= 8 and delta_y <= 10) or
          (delta_x == 9 and delta_y <= 9) or
          (delta_x == 10 and delta_y <= 8) or
          (delta_x == 11 and delta_y <= 6) or
          (delta_x == 12 and delta_y <= 4) or
          (delta_x == 13 and delta_y <= 1)):
        return 'longBomb'
    else:
        return 'outOfRange'

def on_pitch(xpos, ypos):
    return 0 <= xpos < 26 and 0 <= ypos < 15

def other_side(side):
    if side == 'home':
        return 'away'
    elif side == 'away':
        return 'home'
    else:
        raise ValueError('Unrecognised side: ' + side)
        
def previous_step(match, data):
    """Return the previous step from the match"""
    history = Step.objects.filter(match=match).order_by('-history_position')
    return history[1]

# def current_team(match):
#     step_set = Step.objects.filter(match=match).order_by('-history_position')
#     for step in step_set:
#         if step.step_type == 'endTurn':
#             if step.as_dict()['oldSide'] == 'home':
#                 side = 'away'
#             else:
#                 side = 'home'
#             break
#     else:
#         side = match.first_kicking_team
#     if side == 'home':
#         return match.home_team
#     else:
#         return match.away_team



