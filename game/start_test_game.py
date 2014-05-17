from django.contrib.auth.models import User

from game.models import Race, Team, Player, PlayerInGame, create_player, start_match

def create_match():
    # Make the users, if necessary
    for username in ('alice', 'bob'):
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            User.objects.create_user(
                username=username,
                email='james.thomas.allen@gmail.com',
                password='password')
    # Make teams
    human = Race.objects.get(singular='human')
    reavers = Team(race=human, name='Reikland Reavers',
        coach=User.objects.get(username='alice'))
    reavers.save()
    populate_humans(reavers)
    orc = Race.objects.get(singular='orc')
    raiders = Team(race=orc, name='Orcland Raiders',
        coach=User.objects.get(username='bob'))
    raiders.save()
    populate_orcs(raiders)
    match = start_match(reavers, raiders)
    return match

def place_players(match, side, positions_dict):
    """Place the players from one side."""
    if side == 'home':
        team = match.home_team
    else:
        team = match.away_team
    for position, coordinates in positions_dict.items():
        players = PlayerInGame.objects.filter(
            match=match, player__team=team, player__position__title=position)
        for player, (xpos, ypos) in zip(players, coordinates):
            player.xpos = xpos
            player.ypos = ypos
            player.save()
    return

def start_after_kickoff():
    """Place the players and carry out the kickoff."""
    match = create_match()
    human_positions = {
        'Lineman': [[11, 2], [11, 12], [9, 4], [9, 10], [8, 7]],
        'Thrower': [[6, 7]],
        'Blitzer': [[12, 5], [12, 9]],
        'Catcher': [[10, 1], [10, 13]],
        'Ogre': [[12, 7]],
    }
    place_players(match, 'home', human_positions)
    orc_positions = {
        'Lineman': [[13, 3], [13, 11]],
        'Thrower': [[18, 7]],
        'Black Orc Blocker': [[13, 4], [13, 6], [13, 8], [13, 10]],
        'Blitzer': [[13, 2], [13, 12], [15, 5], [15, 9]],
    }
    place_players(match, 'away', orc_positions)
    match.x_ball = 17
    match.y_ball = 5
    match.turn_type = 'normal'
    match.turn_number = 1
    match.current_side = 'away'
    match.save()
    return match
        

def populate_humans(team):
    positions = {
        'Lineman': 5,
        'Thrower': 1,
        'Blitzer': 2,
        'Catcher': 2,
        'Ogre': 1,
    }
    number = 1
    for position_title, quantity in positions.items():
        for _ in range(quantity):
            create_player(
                team, 
                position_title, 
                'Human player ' + str(number), 
                number).save()
            number += 1
    team.rerolls = 4
    team.cash = 20
    team.save()

def populate_orcs(team):
    positions = {
        'Lineman': 2,
        'Thrower': 1,
        'Black Orc Blocker': 4,
        'Blitzer': 4,
    }
    number = 1
    for position_title, quantity in positions.items():
        for _ in range(quantity):
            create_player(
                team, 
                position_title, 
                'Orc player ' + str(number), 
                number).save()
            number += 1
    team.rerolls = 3
    team.cash = 10
    team.save()

