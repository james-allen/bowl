from game.models import Race, Team, Player, Match, PlayerInGame

def start():
    # Make races
    human = Race(singular='human', plural='humans')
    human.save()
    orc = Race(singular='orc', plural='orcs')
    orc.save()
    # Make teams
    reavers = Team(race=human, name='Reikland Reavers')
    reavers.save()
    populate_humans(reavers)
    raiders = Team(race=orc, name='Orcland Raiders')
    raiders.save()
    populate_orcs(raiders)
    match = Match(
        home_team=reavers, away_team=raiders, first_kicking_team='home', 
        x_ball=3, y_ball=1, home_rerolls=reavers.rerolls, 
        away_rerolls=raiders.rerolls)
    match.save()
    xpos = 0
    ypos = 0
    for player in reavers.player_set.all():
        pig = PlayerInGame(
            player, match=match, xpos=xpos, ypos=ypos, on_pitch=True)
        pig.save()
        xpos += 1
        ypos += 1
    ypos = 0
    for player in raiders.player_set.all():
        pig = PlayerInGame(
            player, match=match, xpos=xpos, ypos=ypos, on_pitch=True)
        pig.save()
        xpos += 1
        ypos += 1
        

def populate_humans(team):
    for num in range(1, 6):
        player = Player(
            name='Human player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=50,
            ma=6,
            st=3,
            ag=3,
            av=8,
            skills='',
            normal_skills='G',
            double_skills='ASP',
            )
        player.save()
    for num in range(6, 7):
        player = Player(
            name='Human player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=70,
            ma=6,
            st=3,
            ag=3,
            av=8,
            skills='Sure Hands,Pass',
            normal_skills='GA',
            double_skills='SP',
            )
        player.save()
    for num in range(7, 11):
        player = Player(
            name='Human player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=90,
            ma=7,
            st=3,
            ag=3,
            av=8,
            skills='Block',
            normal_skills='GS',
            double_skills='AP',
            )
        player.save()
    for num in range(11, 12):
        player = Player(
            name='Human player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=140,
            ma=5,
            st=5,
            ag=2,
            av=9,
            skills='Loner,Bone-head,Mighty Blow,Thick Skull,Throw Team-Mate',
            normal_skills='S',
            double_skills='GAP',
            )
        player.save()
    team.rerolls = 3
    team.cash = 30
    team.save()

def populate_orcs(team):
    for num in range(1, 3):
        player = Player(
            name='Orc player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=50,
            ma=5,
            st=3,
            ag=3,
            av=9,
            skills='',
            normal_skills='G',
            double_skills='ASP',
            )
        player.save()
    for num in range(3, 4):
        player = Player(
            name='Orc player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=70,
            ma=5,
            st=3,
            ag=3,
            av=8,
            skills='Sure Hands,Pass',
            normal_skills='GP',
            double_skills='AS',
            )
        player.save()
    for num in range(4, 8):
        player = Player(
            name='Orc player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=80,
            ma=4,
            st=4,
            ag=2,
            av=9,
            skills='',
            normal_skills='GS',
            double_skills='AP',
            )
        player.save()
    for num in range(8, 12):
        player = Player(
            name='Orc player ' + str(num),
            race=team.race,
            team=team,
            number=num,
            value=80,
            ma=6,
            st=3,
            ag=3,
            av=9,
            skills='Block',
            normal_skills='GS',
            double_skills='AP',
            )
        player.save()
    team.rerolls = 3
    team.cash = 10
    team.save()

