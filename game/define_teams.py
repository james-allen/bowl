from game.models import Race, Position

HUMAN = {
    'singular': 'human',
    'plural': 'humans',
    'reroll_cost': 50,
    'positions': [
        (16, 'Lineman', 50, 6, 3, 3, 8, '', 'G', 'ASP', 'human'),
        (4, 'Catcher', 70, 8, 2, 3, 7, 'Catch,Dodge', 'GA', 'SP', 'human'),
        (2, 'Thrower', 70, 6, 4, 4, 8, 'Sure Hands,Pass', 'GP', 'AS', 'human'),
        (4, 'Blitzer', 90, 7, 3, 3, 8, 'Block', 'GS', 'AP', 'human'),
        (1, 'Ogre', 140, 5, 5, 2, 9, 'Loner,Bone-head,Mighty Blow,Thick Skull,Throw Team-Mate', 'S', 'GAP', 'ogre')
        ]
}

ORC = {
    'singular': 'orc',
    'plural': 'orcs',
    'reroll_cost': 60,
    'positions': [
        (16, 'Lineman', 50, 5, 3, 3, 9, '', 'G', 'ASP', 'orc'),
        (4, 'Goblin', 40, 6, 2, 3, 7, 'Right Stuff,Dodge,Stunty', 'A', 'GSP', 'goblin'),
        (2, 'Thrower', 70, 5, 3, 3, 8, 'Sure Hands,Pass', 'GP', 'AS', 'orc'),
        (4, 'Black Orc Blocker', 80, 4, 4, 2, 9, '', 'GS', 'AP', 'orc'),
        (4, 'Blitzer', 80, 6, 3, 3, 9, 'Block', 'GS', 'AP', 'orc'),
        (1, 'Troll', 110, 4, 5, 1, 9, 'Loner,Always Hungry,Mighty Blow,Really Stupid,Regeneration,Throw Team-Mate', 'S', 'GAP', 'troll')
        ]
}

def define_race(data):
    race = Race(
        singular=data['singular'],
        plural=data['plural'],
        reroll_cost=data['reroll_cost']
        )
    race.save()
    for pos in data['positions']:
        position = Position(
            team_race=race,
            max_quantity=pos[0],
            title=pos[1],
            cost=pos[2],
            ma=pos[3],
            st=pos[4],
            ag=pos[5],
            av=pos[6],
            skills=pos[7],
            normal_skills=pos[8],
            double_skills=pos[9],
            race=pos[10]
            )
        position.save()

def define_all():
    define_race(HUMAN)
    define_race(ORC)
