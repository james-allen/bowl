from game.models import Race, Position

AMAZON = {
    'singular': 'amazon',
    'plural': 'amazons',
    'reroll_cost': 50,
    'positions': [
        (16, 'Linewoman', 50, 6, 3, 3, 7, 'Dodge', 'G', 'ASP', 'human'),
        (2, 'Thrower', 70, 6, 3, 3, 7, 'Dodge,Pass', 'GP', 'AS', 'human'),
        (2, 'Catcher', 70, 6, 3, 3, 7, 'Dodge,Catch', 'GA', 'SP', 'human'),
        (4, 'Blitzer', 90, 6, 3, 3, 7, 'Dodge,Block', 'GS', 'AP', 'human'),
        ]
}

HIGH_ELF = {
    'singular': 'high elf',
    'plural': 'high elves',
    'reroll_cost': 50,
    'positions': [
        (16, 'Lineman', 70, 6, 3, 4, 7, '', 'GA', 'SP', 'elf'),
        (2, 'Thrower', 90, 6, 3, 4, 8, 'Pass,Safe Throw', 'GAP', 'S', 'elf'),
        (4, 'Catcher', 90, 8, 3, 4, 7, 'Catch', 'GA', 'SP', 'elf'),
        (2, 'Blitzer', 100, 7, 3, 4, 8, 'Block', 'GA', 'SP', 'elf'),
        ]
}

HUMAN = {
    'singular': 'human',
    'plural': 'humans',
    'reroll_cost': 50,
    'positions': [
        (16, 'Lineman', 50, 6, 3, 3, 8, '', 'G', 'ASP', 'human'),
        (4, 'Catcher', 70, 8, 2, 3, 7, 'Catch,Dodge', 'GA', 'SP', 'human'),
        (2, 'Thrower', 70, 6, 4, 4, 8, 'Sure Hands,Pass', 'GP', 'AS', 'human'),
        (4, 'Blitzer', 90, 7, 3, 3, 8, 'Block', 'GS', 'AP', 'human'),
        (1, 'Ogre', 140, 5, 5, 2, 9, 'Loner,Bone-head,Mighty Blow,Thick Skull,Throw Team-Mate', 'S', 'GAP', 'ogre'),
        ]
}

KHEMRI = {
    'singular': 'khemri',
    'plural': 'khemri',
    'reroll_cost': 70,
    'positions': [
        (16, 'Skeleton', 40, 5, 3, 2, 7, 'Regeneration,Thick Skull', 'G', 'ASP', 'undead'),
        (2, 'Thro-Ra', 70, 6, 3, 2, 7, 'Pass,Regeneration,Sure Hands', 'GP', 'AS', 'undead'),
        (2, 'Blitz-Ra', 90, 6, 3, 2, 8, 'Block,Regeneration', 'GS', 'AP', 'undead'),
        (4, 'Tomb Guardian', 100, 4, 5, 1, 9, 'Decay,Regeneration', 'S', 'GAP', 'undead'),
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
        (1, 'Troll', 110, 4, 5, 1, 9, 'Loner,Always Hungry,Mighty Blow,Really Stupid,Regeneration,Throw Team-Mate', 'S', 'GAP', 'troll'),
        ]
}

UNDEAD = {
    'singular': 'undead',
    'plural': 'undead',
    'reroll_cost': 70,
    'positions': [
        (16, 'Skeleton', 40, 5, 3, 2, 7, 'Regeneration,Thick Skull', 'G', 'ASP', 'undead'),
        (16, 'Zombie', 40, 4, 3, 2, 8, 'Regeneration', 'G', 'ASP', 'undead'),
        (4, 'Ghoul', 70, 7, 3, 3, 7, 'Dodge', 'GA', 'SP', 'undead'),
        (2, 'Wight', 90, 6, 3, 3, 8, 'Block,Regeneration', 'GS', 'AP', 'undead'),
        (2, 'Mummy', 120, 3, 5, 1, 9, 'Mighty Blow,Regeneration', 'S', 'GAP', 'undead'),
        ]
}

def define_race(data):
    # Don't define the race if it already exists
    try:
        Race.objects.get(singular=data['singular'])
    except Race.DoesNotExist:
        pass
    else:
        return
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
    define_race(AMAZON)
    define_race(HIGH_ELF)
    define_race(HUMAN)
    define_race(KHEMRI)
    define_race(ORC)
    define_race(UNDEAD)
