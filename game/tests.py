import json
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User

from game.models import Race, Team, Player, PlayerInGame, Step, Position
from game.models import start_match, create_team, create_player
from game.define_teams import define_all

class StepTests(TestCase):

    def test_move_step(self):
        """
        Test that a player is successfully moved by a move step.
        """
        match = create_test_match()
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        pig = place_player(match, 'home', 1, x0, y0, False)
        # Move them
        step = Step.objects.create(
            step_type='move',
            action='move',
            match=match,
            history_position=0,
            properties=json.dumps({
                'action': 'move',
                'x1': str(x1),
                'y1': str(y1),
                'dodge': 'false',
                'side': 'home',
                'num': str(pig.player.number),
            }))
        step.save()
        match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)

    def test_move_with_ball_step(self):
        """
        Test that a player and the ball are successfully moved by a move step.
        """
        match = create_test_match()
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        pig = place_player(match, 'home', 1, x0, y0, True)
        # Move them
        step = Step.objects.create(
            step_type='move',
            action='move',
            match=match,
            history_position=0,
            properties=json.dumps({
                'action': 'move',
                'x1': str(x1),
                'y1': str(y1),
                'dodge': 'false',
                'side': 'home',
                'num': str(pig.player.number),
            }))
        step.save()
        match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)
        self.assertEqual(match.x_ball, x1)
        self.assertEqual(match.y_ball, y1)

    @patch('random.randint', lambda a, b: 6)
    def test_dodge_success_step(self):
        """
        Test that a successful dodge is returned.
        """
        match = create_test_match()
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        pig = place_player(match, 'home', 1, x0, y0, True)
        # Move them
        step = Step.objects.create(
            step_type='move',
            action='move',
            match=match,
            history_position=0,
            properties=json.dumps({
                'action': 'move',
                'x1': str(x1),
                'y1': str(y1),
                'dodge': 'true',
                'side': 'home',
                'num': str(pig.player.number),
            }))
        step.save()
        result = match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertEqual(result['success'], True)
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)
        self.assertEqual(pig.down, False)

    @patch('random.randint', lambda a, b: 1)
    def test_dodge_failure_step(self):
        """
        Test that a failed dodge is returned.
        """
        match = create_test_match()
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        pig = place_player(match, 'home', 1, x0, y0, True)
        # Move them
        step = Step.objects.create(
            step_type='move',
            action='move',
            match=match,
            history_position=0,
            properties=json.dumps({
                'action': 'move',
                'x1': str(x1),
                'y1': str(y1),
                'dodge': 'true',
                'side': 'home',
                'num': str(pig.player.number),
            }))
        step.save()
        result = match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertEqual(result['success'], False)
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)
        # The player is not knocked down yet, as they could reroll
        self.assertEqual(pig.down, False)

    def test_push_step(self):
        """
        Test that a player is successfully moved by a push step.
        """
        match = create_test_match()
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        pig = place_player(match, 'home', 1, x0, y0, False)
        # Move them
        step = Step.objects.create(
            step_type='push',
            action='block',
            match=match,
            history_position=0,
            properties=json.dumps({
                'action': 'block',
                'x1': str(x1),
                'y1': str(y1),
                'dodge': 'false',
                'side': 'home',
                'num': str(pig.player.number),
                'offPitch': 'false',
            }))
        step.save()
        match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)

    def test_push_with_ball_step(self):
        """
        Test that a player and the ball are successfully moved by a push step.
        """
        match = create_test_match()
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        pig = place_player(match, 'home', 1, x0, y0, True)
        # Move them
        step = Step.objects.create(
            step_type='push',
            action='block',
            match=match,
            history_position=0,
            properties=json.dumps({
                'action': 'push',
                'x1': str(x1),
                'y1': str(y1),
                'dodge': 'false',
                'side': 'home',
                'num': str(pig.player.number),
                'offPitch': 'false',
            }))
        step.save()
        match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)
        self.assertEqual(match.x_ball, x1)
        self.assertEqual(match.y_ball, y1)

    @patch('random.randint', lambda a, b: 1)
    def test_push_off_pitch_step(self):
        """
        Test that a player pushed off the pitch is placed in the subs bench
        if not injured
        """
        match = create_test_match()
        # Get a player
        x0, y0 = 15, 0
        x1, y1 = x0+1, -1
        pig = place_player(match, 'home', 1, x0, y0, False)
        # Move them
        step = Step.objects.create(
            step_type='push',
            action='block',
            match=match,
            history_position=0,
            properties=json.dumps({
                'action': 'block',
                'x1': str(x1),
                'y1': str(y1),
                'dodge': 'false',
                'side': 'home',
                'num': str(pig.player.number),
                'offPitch': 'true',
            }))
        step.save()
        match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertEqual(pig.on_pitch, False)
        self.assertEqual(pig.knocked_out, False)
        self.assertEqual(pig.casualty, False)

    def test_block_equal_strengths_step(self):
        """
        Test that a block between players of equal strength returns valid
        results.
        """
        match = create_test_match('human', 'orc')
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        # Blitzer, strength 3
        attacker = place_player(match, 'home', 5, x0, y0, False)
        # Blitzer, strength 3
        defender = place_player(match, 'away', 1, x1, y1, False)
        # Throw the block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 3)
        self.assertEqual(result['nDice'], 1)

    def test_block_attacker_strong_step(self):
        """
        Test that a block where the attacker is stronger returns valid
        results.
        """
        match = create_test_match('human', 'orc')
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        # Ogre, strength 5
        attacker = place_player(match, 'home', 3, x0, y0, False)
        # Blitzer, strength 3
        defender = place_player(match, 'away', 1, x1, y1, False)
        # Throw the block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 5)
        self.assertEqual(result['defenceSt'], 3)
        self.assertEqual(result['nDice'], 2)

    def test_block_defender_strong_step(self):
        """
        Test that a block where the defender is stronger returns valid
        results.
        """
        match = create_test_match('human', 'orc')
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        # Ogre, strength 5
        defender = place_player(match, 'home', 3, x0, y0, False)
        # Blitzer, strength 3
        attacker = place_player(match, 'away', 1, x1, y1, False)
        # Throw the block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 5)
        self.assertEqual(result['nDice'], 2)

    def test_block_attacker_very_strong_step(self):
        """
        Test that a block where the attacker is much stronger returns valid
        results.
        """
        match = create_test_match('human', 'orc')
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        # Catcher, strength 2
        defender = place_player(match, 'home', 1, x0, y0, False)
        # Troll, strength 5
        attacker = place_player(match, 'away', 5, x1, y1, False)
        # Throw the block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 5)
        self.assertEqual(result['defenceSt'], 2)
        self.assertEqual(result['nDice'], 3)

    def test_block_defender_very_strong_step(self):
        """
        Test that a block where the defender is much stronger returns valid
        results.
        """
        match = create_test_match('human', 'orc')
        # Get a player
        x0, y0 = 15, 5
        x1, y1 = x0+1, y0+1
        # Catcher, strength 2
        attacker = place_player(match, 'home', 1, x0, y0, False)
        # Troll, strength 5
        defender = place_player(match, 'away', 5, x1, y1, False)
        # Throw the block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 2)
        self.assertEqual(result['defenceSt'], 5)
        self.assertEqual(result['nDice'], 3)

    def test_block_assists_step(self):
        """
        Test that assists are correctly found and counted.
        """
        match = create_test_match('human', 'orc')
        # Get attacker and defender
        x0, y0 = 15, 5
        # Blitzer, strength 3
        attacker = place_player(match, 'home', 5, x0, y0, False)
        # Blitzer, strength 3
        defender = place_player(match, 'away', 1, x0+1, y0, False)
        # Place an assisting player for the attacker
        attack_1 = place_player(match, 'home', 1, x0, y0+1, False)
        # Throw a block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 3)
        # Place an assisting player for the defender
        defend_1 = place_player(match, 'away', 2, x0+1, y0-1, False)
        # Throw a block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 4)
        # Place a tackle zone on the attacking assist to negate it
        defend_2 = place_player(match, 'away', 3, x0+1, y0+1, False)
        # Throw a block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 4)
        # Place a tackle zone on the defending assist to negate it
        attack_2 = place_player(match, 'home', 2, x0, y0-1, False)
        # Throw a block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 3)
        # Knock one of the extra players over and remove their tackle zones
        defend_2.down = True
        defend_2.tackle_zones = False
        defend_2.save()
        # Throw a block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 3)
        # Remove tackle zones from another player without knocking them down
        attack_2.tackle_zones = False
        attack_2.save()
        # Throw a block
        step = create_test_block_step(match, attacker, defender)
        step.save()
        result = match.resolve(step)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 4)
        
        




def place_player(match, side, number, xpos, ypos, has_ball):
    """
    Select and place a player in the given position.
    """
    if side == 'home':
        team = match.home_team
    else:
        team = match.away_team
    pig = PlayerInGame.objects.get(
        match=match, player__team=team, player__number=number
    )
    pig.xpos = xpos
    pig.ypos = ypos
    pig.on_pitch = True
    pig.has_ball = has_ball
    pig.save()
    if has_ball:
        match.x_ball = xpos
        match.y_ball = ypos
        match.save()
    return pig


def create_test_match(home_race_singular=None, away_race_singular=None):
    """
    Create a match with all the players sitting on the bench.
    """
    home_team = create_test_team(home_race_singular)
    away_team = create_test_team(away_race_singular)
    match = start_match(home_team, away_team)
    for pig in PlayerInGame.objects.filter(match=match):
        pig.on_pitch = False
        pig.save()
    match.turn_type = 'normal'
    match.n_to_place = 0
    match.save()
    return match

def create_test_team(race_singular=None):
    """
    Create a test team.
    """
    define_all()
    coach = create_test_user()
    for idx, race in enumerate(Race.objects.all().order_by('singular')):
        name = 'Team {}'.format(idx)
        try:
            Team.objects.get(name=name)
        except Team.DoesNotExist:
            break
    else:
        raise ValueError('Ran out of test races')
    if race_singular is not None:
        race = Race.objects.get(singular=race_singular)
    team = create_team(name, race, coach,
        color_home_primary='31,120,180', color_home_secondary='51,160,44',
        color_away_primary='227,26,28', color_away_secondary='51,160,44',
    )
    team.save()
    for _ in range(11):
        player = create_test_player(team)
        player.save()
    return team

def create_test_user():
    """
    Create a test user.
    """
    idx = 0
    while True:
        username = 'User {}'.format(idx)
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            break
        idx += 1
    user = User.objects.create(
        username=username,
        email='test@example.com',
        password='password'
    )
    user.save()
    return user

def create_test_player(team):
    """
    Create a test player in the given team.
    """
    number = 1
    while True:
        try:
            Player.objects.get(team=team, number=number)
        except Player.DoesNotExist:
            break
        number += 1
    position_list = Position.objects.filter(team_race=team.race)
    position_list = position_list.order_by('title')
    position_title = position_list[number % len(position_list)].title
    name = 'Player {}'.format(number)
    player = create_player(team, position_title, name, number)
    player.save()
    return player

def create_test_block_step(match, attacker, defender):
    """
    Create a step in which the attacker blocks the defender.
    """
    if attacker.player.team == match.home_team:
        side = 'home'
    else:
        side = 'away'
    history_saved = Step.objects.filter(match=match).values_list(
        'history_position', flat=True).order_by('history_position')
    if len(history_saved) == 0:
        history_position = 0
    else:
        history_position = history_saved[len(history_saved)-1] + 1
    step = Step.objects.create(
        step_type='block',
        action='block',
        match=match,
        history_position=history_position,
        properties=json.dumps({
            'action': 'block',
            'x1': str(defender.xpos),
            'y1': str(defender.ypos),
            'side': side,
            'num': str(attacker.player.number),
            'targetNum': str(defender.player.number)
        })
    )
    return step
