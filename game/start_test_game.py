from game.models import Race, Team, Player, create_player, start_match

def start():
    # Make teams
    human = Race.objects.get(singular='human')
    reavers = Team(race=human, name='Reikland Reavers')
    reavers.save()
    populate_humans(reavers)
    orc = Race.objects.get(singular='orc')
    raiders = Team(race=orc, name='Orcland Raiders')
    raiders.save()
    populate_orcs(raiders)
    match = start_match(reavers, raiders)
        

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
                'Human player ' + str(number), 
                number).save()
            number += 1
    team.rerolls = 3
    team.cash = 10
    team.save()

