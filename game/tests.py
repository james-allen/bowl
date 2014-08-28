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


def create_test_match():
    """
    Create a match with all the players sitting on the bench.
    """
    home_team = create_test_team()
    away_team = create_test_team()
    match = start_match(home_team, away_team)
    for pig in PlayerInGame.objects.filter(match=match):
        pig.on_pitch = False
        pig.save()
    match.turn_type = 'normal'
    match.n_to_place = 0
    match.save()
    return match

def create_test_team():
    """
    Create a test team.
    """
    define_all()
    coach = create_test_user()
    for idx, race in enumerate(Race.objects.all()):
        name = 'Team {}'.format(idx)
        try:
            Team.objects.get(name=name)
        except Team.DoesNotExist:
            break
    else:
        raise ValueError('Ran out of test races')
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
    position_title = Position.objects.filter(team_race=team.race)[0].title
    name = 'Player {}'.format(number)
    player = create_player(team, position_title, name, number)
    player.save()
    return player


