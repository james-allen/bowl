from game.models import PlayerInGame, Step, set_kickoff

import random

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



