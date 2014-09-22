import json
from unittest.mock import patch
from itertools import product

from django.test import TestCase
from django.contrib.auth.models import User

from game.models import Race, Team, Player, PlayerInGame, Step, Position, Match
from game.models import start_match, create_team, create_player
from game.define_teams import define_all
from game.utils import other_side

class RiggedDice():
    """
    A rigged dice for testing. Initialise with the desired sequence of rolls.
    """

    def __init__(self, seq):
        self.seq = seq
        self.idx = 0
        self.n = len(seq)

    def __call__(self, a, b):
        value = self.seq[self.idx % self.n]
        self.idx += 1
        return value


class BloodBowlTestCase(TestCase):
    """
    Generic test case class for Blood Bowl tests.

    Classes inheriting from this class must define a setUp() method that
    creates a self.match
    """

    def place_player_of_position(self, side, position, xpos, ypos,
                                 has_ball=False):
        """
        Find a player of the suitable position and place them on the pitch.
        """
        if side == 'home':
            team = self.match.home_team
        else:
            team = self.match.away_team
        if position is None:
            pig = PlayerInGame.objects.filter(
                match=self.match, player__team=team,
                on_pitch=False
            )[0]
        else:
            pig = PlayerInGame.objects.filter(
                match=self.match, player__team=team,
                player__position__title=position,
                on_pitch=False
            )[0]
        pig.xpos = xpos
        pig.ypos = ypos
        pig.on_pitch = True
        pig.has_ball = has_ball
        pig.save()
        if has_ball:
            self.match.x_ball = xpos
            self.match.y_ball = ypos
            self.match.save()
        return pig

    def place_player(self, side, xpos, ypos, has_ball=False):
        """
        Find a player of any position and place them on the pitch.
        """
        return self.place_player_of_position(side, None, xpos, ypos, has_ball)

    def create_test_step(self, step_type, action, properties):
        """
        Create a step object.
        """
        history_saved = Step.objects.filter(match=self.match).values_list(
            'history_position', flat=True).order_by('history_position')
        if len(history_saved) == 0:
            history_position = 0
        else:
            history_position = history_saved[len(history_saved)-1] + 1
        step = Step.objects.create(
            step_type=step_type,
            action=action,
            match=self.match,
            history_position=history_position,
            properties=json.dumps(properties)
        )
        return step

    def side_of_team(self, team):
        """
        Return 'home' or 'away' corresponding to the Team.
        """
        if team == self.match.home_team:
            side = 'home'
        elif team == self.match.away_team:
            side = 'away'
        else:
            raise ValueError('The provided team is not in the match.')
        return side

    def side_of_pig(self, pig):
        """
        Return 'home' or 'away' corresponding to the PlayerInGame.
        """
        return self.side_of_team(pig.player.team)

    def reload_pig(self, pig):
        """
        Reload the given player from the database.
        """
        return PlayerInGame.objects.get(
            match=self.match, player=pig.player)

    def reload_match(self):
        """
        Reload the match that's being tested.
        """
        self.match = Match.objects.get(id=self.match.id)
        return self.match



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
                'dodge': False,
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
                'dodge': False,
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
                'dodge': True,
                'side': 'home',
                'num': str(pig.player.number),
            }))
        step.save()
        result = match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertTrue(result['success'])
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)
        self.assertFalse(pig.down)

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
                'dodge': True,
                'side': 'home',
                'num': str(pig.player.number),
            }))
        step.save()
        result = match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertFalse(result['success'])
        self.assertEqual(pig.xpos, x1)
        self.assertEqual(pig.ypos, y1)
        # The player is not knocked down yet, as they could reroll
        self.assertFalse(pig.down)

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
                'dodge': False,
                'side': 'home',
                'num': str(pig.player.number),
                'offPitch': False,
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
                'dodge': False,
                'side': 'home',
                'num': str(pig.player.number),
                'offPitch': False,
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
                'dodge': False,
                'side': 'home',
                'num': str(pig.player.number),
                'offPitch': True,
            }))
        step.save()
        match.resolve(step)
        # Reload the player
        pig = PlayerInGame.objects.get(match=match, player=pig.player)
        self.assertFalse(pig.on_pitch)
        self.assertFalse(pig.knocked_out)
        self.assertFalse(pig.casualty)


class BlockAndFoulTests(BloodBowlTestCase):

    xpos = 15
    ypos = 5

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')

    def throw_block(self, attacker, defender):
        """
        Create and process a step in which the attacker blocks the defender.
        """
        step = self.create_test_block_step(attacker, defender)
        step.save()
        result = self.match.resolve(step)
        return result

    def create_test_block_step(self, attacker, defender):
        """
        Create a step in which the attacker blocks the defender.
        """
        properties = {
            'action': 'block',
            'x1': str(defender.xpos),
            'y1': str(defender.ypos),
            'side': self.side_of_pig(attacker),
            'num': str(attacker.player.number),
            'targetNum': str(defender.player.number),
        }
        return self.create_test_step('block', 'block', properties)

    def commit_foul(self, attacker, defender):
        """
        Create and process a step in which the attacker fouls the defender.
        """
        step = self.create_test_foul_step(attacker, defender)
        step.save()
        result = self.match.resolve(step)
        return result

    def create_test_foul_step(self, attacker, defender):
        """
        Create a step in which the attacker fouls the defender.
        """
        if attacker.player.team == self.match.home_team:
            side = 'home'
        else:
            side = 'away'
        history_saved = Step.objects.filter(match=self.match).values_list(
            'history_position', flat=True).order_by('history_position')
        if len(history_saved) == 0:
            history_position = 0
        else:
            history_position = history_saved[len(history_saved)-1] + 1
        step = Step.objects.create(
            step_type='foul',
            action='foul',
            match=self.match,
            history_position=history_position,
            properties=json.dumps({
                'action': 'foul',
                'x1': str(defender.xpos),
                'y1': str(defender.ypos),
                'side': side,
                'num': str(attacker.player.number),
                'targetNum': str(defender.player.number)
            })
        )
        return step

    def test_block_equal_strengths_step(self):
        """
        Test that a block between players of equal strength returns valid
        results.
        """
        # Blitzer, strength 3
        attacker = self.place_player_of_position(
            'home', 'Blitzer', self.xpos, self.ypos)
        # Blitzer, strength 3
        defender = self.place_player_of_position(
            'away', 'Blitzer', self.xpos+1, self.ypos)
        # Throw the block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 3)
        self.assertEqual(result['nDice'], 1)

    def test_block_attacker_strong_step(self):
        """
        Test that a block where the attacker is stronger returns valid
        results.
        """
        # Ogre, strength 5
        attacker = self.place_player_of_position(
            'home', 'Ogre', self.xpos, self.ypos)
        # Blitzer, strength 3
        defender = self.place_player_of_position(
            'away', 'Blitzer', self.xpos+1, self.ypos)
        # Throw the block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 5)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 5)
        self.assertEqual(result['defenceSt'], 3)
        self.assertEqual(result['nDice'], 2)

    def test_block_defender_strong_step(self):
        """
        Test that a block where the defender is stronger returns valid
        results.
        """
        # Ogre, strength 5
        defender = self.place_player_of_position(
            'home', 'Ogre', self.xpos, self.ypos)
        # Blitzer, strength 3
        attacker = self.place_player_of_position(
            'away', 'Blitzer', self.xpos+1, self.ypos)
        # Throw the block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 5)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 5)
        self.assertEqual(result['nDice'], 2)

    def test_block_attacker_very_strong_step(self):
        """
        Test that a block where the attacker is much stronger returns valid
        results.
        """
        # Catcher, strength 2
        defender = self.place_player_of_position(
            'home', 'Catcher', self.xpos, self.ypos)
        # Troll, strength 5
        attacker = self.place_player_of_position(
            'away', 'Troll', self.xpos+1, self.ypos)
        # Throw the block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 5)
        self.assertEqual(result['rawDefenceSt'], 2)
        self.assertEqual(result['attackSt'], 5)
        self.assertEqual(result['defenceSt'], 2)
        self.assertEqual(result['nDice'], 3)

    def test_block_defender_very_strong_step(self):
        """
        Test that a block where the defender is much stronger returns valid
        results.
        """
        # Catcher, strength 2
        attacker = self.place_player_of_position(
            'home', 'Catcher', self.xpos, self.ypos)
        # Troll, strength 5
        defender = self.place_player_of_position(
            'away', 'Troll', self.xpos+1, self.ypos)
        # Throw the block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 2)
        self.assertEqual(result['rawDefenceSt'], 5)
        self.assertEqual(result['attackSt'], 2)
        self.assertEqual(result['defenceSt'], 5)
        self.assertEqual(result['nDice'], 3)

    def test_block_assists_step(self):
        """
        Test that assists are correctly found and counted.
        """
        # Get attacker and defender
        # Blitzer, strength 3
        attacker = self.place_player_of_position(
            'home', 'Blitzer', self.xpos, self.ypos)
        # Blitzer, strength 3
        defender = self.place_player_of_position(
            'away', 'Blitzer', self.xpos+1, self.ypos)
        # Place an assisting player for the attacker
        attack_1 = self.place_player('home', self.xpos, self.ypos+1)
        # Throw a block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 3)
        # Place an assisting player for the defender
        defend_1 = self.place_player('away', self.xpos+1, self.ypos-1)
        # Throw a block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 4)
        # Place a tackle zone on the attacking assist to negate it
        defend_2 = self.place_player('away', self.xpos+1, self.ypos+1)
        # Throw a block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 4)
        # Place a tackle zone on the defending assist to negate it
        attack_2 = self.place_player('home', self.xpos, self.ypos-1)
        # Throw a block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 3)
        self.assertEqual(result['defenceSt'], 3)
        # Knock one of the extra players over and remove their tackle zones
        defend_2.down = True
        defend_2.tackle_zones = False
        defend_2.save()
        # Throw a block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 3)
        # Remove tackle zones from another player without knocking them down
        attack_2.tackle_zones = False
        attack_2.save()
        # Throw a block
        result = self.throw_block(attacker, defender)
        self.assertEqual(result['rawAttackSt'], 3)
        self.assertEqual(result['rawDefenceSt'], 3)
        self.assertEqual(result['attackSt'], 4)
        self.assertEqual(result['defenceSt'], 4)
        
    @patch('random.randint', RiggedDice((1, 2)))
    def test_foul_modifiers(self):
        """
        Test that foul modifiers are correctly calculated.
        """
        # Get attacker and defender
        attacker = self.place_player('home', self.xpos, self.ypos)
        defender = self.place_player('away', self.xpos+1, self.ypos)
        defender.down = True
        defender.tackle_zones = False
        defender.save()
        # A bog-standard foul
        result = self.commit_foul(attacker, defender)
        self.assertEqual(result['armourRoll']['modifiedResult'] -
                         result['armourRoll']['rawResult'], 0)
        # Place an assisting player for the attacker
        attack_1 = self.place_player('home', self.xpos, self.ypos+1)
        # Foul
        result = self.commit_foul(attacker, defender)
        self.assertEqual(result['armourRoll']['modifiedResult'] -
                         result['armourRoll']['rawResult'], 1)
        # Place an assisting player for the defender
        defend_1 = self.place_player('away', self.xpos+1, self.ypos-1)
        # Foul
        result = self.commit_foul(attacker, defender)
        self.assertEqual(result['armourRoll']['modifiedResult'] -
                         result['armourRoll']['rawResult'], 0)
        # Place a tackle zone on the attacking assist to negate it
        defend_2 = self.place_player('away', self.xpos+1, self.ypos+1)
        # Foul
        result = self.commit_foul(attacker, defender)
        self.assertEqual(result['armourRoll']['modifiedResult'] -
                         result['armourRoll']['rawResult'], -1)
        # Place a tackle zone on the defending assist to negate it
        attack_2 = self.place_player('home', self.xpos, self.ypos-1)
        # Foul
        result = self.commit_foul(attacker, defender)
        self.assertEqual(result['armourRoll']['modifiedResult'] -
                         result['armourRoll']['rawResult'], 0)
        # Knock one of the extra players over and remove their tackle zones
        defend_2.down = True
        defend_2.tackle_zones = False
        defend_2.save()
        # Foul
        result = self.commit_foul(attacker, defender)
        self.assertEqual(result['armourRoll']['modifiedResult'] -
                         result['armourRoll']['rawResult'], 1)
        # Remove tackle zones from another player without knocking them down
        attack_2.tackle_zones = False
        attack_2.save()
        # Foul
        result = self.commit_foul(attacker, defender)
        self.assertEqual(result['armourRoll']['modifiedResult'] -
                         result['armourRoll']['rawResult'], 0)
        
    def test_foul_sent_off(self):
        """
        Test that players are sent off for double throws.
        """
        # Get attacker and defender
        attacker = self.place_player('home', self.xpos, self.ypos)
        defender = self.place_player('away', self.xpos+1, self.ypos)
        defender.down = True
        defender.tackle_zones = False
        defender.save()
        # No doubles
        with patch('random.randint', RiggedDice((5, 6, 5, 6))):
            result = self.commit_foul(attacker, defender)
        self.assertFalse(result['sentOff'])
        attacker = PlayerInGame.objects.get(
            match=self.match, player=attacker.player)
        self.assertTrue(attacker.on_pitch)
        self.assertFalse(attacker.sent_off)
        # Double in injury dice
        with patch('random.randint', RiggedDice((5, 6, 1, 1))):
            result = self.commit_foul(attacker, defender)
        self.assertTrue(result['sentOff'])
        attacker = PlayerInGame.objects.get(
            match=self.match, player=attacker.player)
        self.assertFalse(attacker.on_pitch)
        self.assertTrue(attacker.sent_off)
        # Double in armour dice
        with patch('random.randint', RiggedDice((6, 6, 1, 2))):
            result = self.commit_foul(attacker, defender)
        self.assertTrue(result['sentOff'])
        attacker = PlayerInGame.objects.get(
            match=self.match, player=attacker.player)
        self.assertFalse(attacker.on_pitch)
        self.assertTrue(attacker.sent_off)


class SelectBlockDiceTests(BloodBowlTestCase):

    xpos = 15
    ypos = 5

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')

    def select_dice(self, attacker, defender, selection):
        """
        Create and process a step in which the player selects a block result.
        """
        step = self.create_test_select_block_dice_step(
            attacker, defender, selection)
        step.save()
        result = self.match.resolve(step)
        return result

    def create_test_select_block_dice_step(self, attacker, defender,
                                           selection):
        """
        Create a step in which the player selects a block result.
        """
        properties = {
            'action': 'block',
            'selectedDice': selection,
            'x0': str(attacker.xpos),
            'y0': str(attacker.ypos),
            'x1': str(defender.xpos),
            'y1': str(defender.ypos),
            'side': self.side_of_pig(attacker),
            'num': str(attacker.player.number),
            'targetSide': self.side_of_pig(defender),
            'targetNum': str(defender.player.number),
        }
        return self.create_test_step('selectBlockDice', 'block', properties)

    def test_attacker_down(self):
        """Test that the correct details are returned for an attacker down."""
        attacker = self.place_player_of_position(
            'home', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Lineman', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'attackerDown')
        self.assertEqual(len(result['nextStep']), 1)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], attacker.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(next_step['perpNum'], defender.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(defender))
        self.assertFalse(next_step['mightyBlow'])

    def test_attacker_down_mighty_blow(self):
        """Test that mightyBlow is set to 'armour' automatically."""
        attacker = self.place_player_of_position(
            'home', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Troll', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'attackerDown')
        self.assertEqual(len(result['nextStep']), 1)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], attacker.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(next_step['perpNum'], defender.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(defender))
        self.assertEqual(next_step['mightyBlow'], 'armour')

    def test_both_down_no_block(self):
        """Test that both players are knocked down for a bothDown result."""
        attacker = self.place_player_of_position(
            'home', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Lineman', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'bothDown')
        self.assertEqual(len(result['nextStep']), 2)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(next_step['perpNum'], attacker.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(attacker))
        self.assertFalse(next_step['mightyBlow'])
        next_step = result['nextStep'][1]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], attacker.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(next_step['perpNum'], defender.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(defender))
        self.assertFalse(next_step['mightyBlow'])

    def test_both_down_attacker_block(self):
        """Test that only the defender goes down if the attacker has Block."""
        attacker = self.place_player_of_position(
            'home', 'Blitzer', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Lineman', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'bothDown')
        self.assertEqual(len(result['nextStep']), 1)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(next_step['perpNum'], attacker.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(attacker))
        self.assertFalse(next_step['mightyBlow'])

    def test_both_down_defender_block(self):
        """Test that only the attacker goes down if the defender has Block."""
        attacker = self.place_player_of_position(
            'home', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Blitzer', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'bothDown')
        self.assertEqual(len(result['nextStep']), 1)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], attacker.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(next_step['perpNum'], defender.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(defender))
        self.assertFalse(next_step['mightyBlow'])

    def test_both_down_both_block(self):
        """Test that nothing happens if both players have Block."""
        attacker = self.place_player_of_position(
            'home', 'Blitzer', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Blitzer', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'bothDown')
        self.assertFalse('nextStep' in result)

    def test_pushed(self):
        """Test that a push step is successfully created."""
        attacker = self.place_player_of_position(
            'home', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Lineman', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'pushed')
        self.assertEqual(len(result['nextStep']), 2)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'push')
        self.assertEqual(int(next_step['num']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        next_step = result['nextStep'][1]
        self.assertEqual(next_step['stepType'], 'followUp')
        self.assertEqual(int(next_step['targetNum']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(int(next_step['num']), attacker.player.number)
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        self.assertIsNone(next_step['choice'])

    def test_defender_stumbles(self):
        """Test that the defender is pushed and knocked over."""
        attacker = self.place_player_of_position(
            'home', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'away', 'Lineman', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'defenderStumbles')
        self.assertEqual(len(result['nextStep']), 3)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'push')
        self.assertEqual(int(next_step['num']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        next_step = result['nextStep'][1]
        self.assertEqual(next_step['stepType'], 'followUp')
        self.assertEqual(int(next_step['targetNum']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(int(next_step['num']), attacker.player.number)
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        self.assertIsNone(next_step['choice'])
        next_step = result['nextStep'][2]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(next_step['perpNum'], attacker.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(attacker))

    def test_defender_stumbles_dodge(self):
        """Test that the defender is not knocked over with Dodge."""
        attacker = self.place_player_of_position(
            'away', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'home', 'Catcher', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'defenderStumbles')
        self.assertEqual(len(result['nextStep']), 2)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'push')
        self.assertEqual(int(next_step['num']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        next_step = result['nextStep'][1]
        self.assertEqual(next_step['stepType'], 'followUp')
        self.assertEqual(int(next_step['targetNum']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(int(next_step['num']), attacker.player.number)
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        self.assertIsNone(next_step['choice'])

    def test_defender_down(self):
        """Test that the defender is knocked down, even with Dodge."""
        attacker = self.place_player_of_position(
            'away', 'Lineman', self.xpos, self.ypos)
        defender = self.place_player_of_position(
            'home', 'Catcher', self.xpos+1, self.ypos)
        result = self.select_dice(attacker, defender, 'defenderDown')
        self.assertEqual(len(result['nextStep']), 3)
        next_step = result['nextStep'][0]
        self.assertEqual(next_step['stepType'], 'push')
        self.assertEqual(int(next_step['num']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        next_step = result['nextStep'][1]
        self.assertEqual(next_step['stepType'], 'followUp')
        self.assertEqual(int(next_step['targetNum']), defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(attacker))
        self.assertEqual(int(next_step['num']), attacker.player.number)
        self.assertEqual(int(next_step['x0']), attacker.xpos)
        self.assertEqual(int(next_step['y0']), attacker.ypos)
        self.assertEqual(int(next_step['x1']), defender.xpos)
        self.assertEqual(int(next_step['y1']), defender.ypos)
        self.assertIsNone(next_step['choice'])
        next_step = result['nextStep'][2]
        self.assertEqual(next_step['stepType'], 'knockDown')
        self.assertEqual(next_step['num'], defender.player.number)
        self.assertEqual(next_step['side'], self.side_of_pig(defender))
        self.assertEqual(next_step['perpNum'], attacker.player.number)
        self.assertEqual(next_step['perpSide'], self.side_of_pig(attacker))
        



class KnockDownTests(BloodBowlTestCase):

    xpos = 15
    ypos = 5

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')

    def create_test_knock_down_step(self, victim, mighty_blow=False):
        """
        Create a knock down step for the unfortunate victim.
        """
        properties = {
            'action': 'move',
            'num': victim.player.number,
            'side': self.side_of_pig(victim),
            'mightyBlow': mighty_blow,
        }
        return self.create_test_step('knockDown', 'move', properties)

    def create_test_stand_up_step(self, pig):
        """
        Create a step where the player stands up.
        """
        properties = {
            'action': 'move',
            'num': pig.player.number,
            'side': self.side_of_pig(pig),
        }
        return self.create_test_step('standUp', 'move', properties)

    def test_knock_down_fail_armour(self):
        """
        Test that the player is knocked down and loses the ball.
        """
        victim = self.place_player('home', self.xpos, self.ypos, True)
        step = self.create_test_knock_down_step(victim, False)
        with patch('random.randint', RiggedDice((1, 1))):
            result = self.match.resolve(step)
        victim = PlayerInGame.objects.get(
            match=self.match, player=victim.player)
        self.assertTrue(victim.down)
        self.assertFalse(victim.tackle_zones)
        self.assertFalse(victim.has_ball)
        self.assertTrue(victim.on_pitch)
        self.assertFalse(victim.stunned)
        self.assertFalse(result['armourRoll']['success'])

    def test_knock_down_stunned(self):
        """
        Test that the victim is stunned.
        """
        victim = self.place_player('home', self.xpos, self.ypos, True)
        step = self.create_test_knock_down_step(victim, False)
        with patch('random.randint', RiggedDice((6, 6, 1, 1))):
            result = self.match.resolve(step)
        victim = PlayerInGame.objects.get(
            match=self.match, player=victim.player)
        self.assertTrue(victim.down)
        self.assertFalse(victim.tackle_zones)
        self.assertFalse(victim.has_ball)
        self.assertTrue(victim.on_pitch)
        self.assertTrue(victim.stunned)
        self.assertTrue(result['armourRoll']['success'])
        self.assertEqual(result['injuryRoll']['result'], 'stunned')

    def test_knock_down_knocked_out(self):
        """
        Test that the victim is knocked out.
        """
        victim = self.place_player('home', self.xpos, self.ypos, True)
        step = self.create_test_knock_down_step(victim, False)
        with patch('random.randint', RiggedDice((6, 6, 4, 5))):
            result = self.match.resolve(step)
        victim = PlayerInGame.objects.get(
            match=self.match, player=victim.player)
        self.assertFalse(victim.on_pitch)
        self.assertTrue(victim.knocked_out)
        self.assertTrue(result['armourRoll']['success'])
        self.assertEqual(result['injuryRoll']['result'], 'knockedOut')

    def test_knock_down_casualty(self):
        """
        Test that the victim is a casualty.
        """
        victim = self.place_player('home', self.xpos, self.ypos, True)
        step = self.create_test_knock_down_step(victim, False)
        with patch('random.randint', RiggedDice((6, 6, 6, 6))):
            result = self.match.resolve(step)
        victim = PlayerInGame.objects.get(
            match=self.match, player=victim.player)
        self.assertFalse(victim.on_pitch)
        self.assertTrue(victim.casualty)
        self.assertTrue(result['armourRoll']['success'])
        self.assertEqual(result['injuryRoll']['result'], 'casualty')

    def test_knock_down_mighty_blow_armour(self):
        """
        Test that a modifier is added to the armour roll.
        """
        victim = self.place_player('home', self.xpos, self.ypos, True)
        step = self.create_test_knock_down_step(victim, 'armour')
        with patch('random.randint', RiggedDice((6, 6, 1, 1))):
            result = self.match.resolve(step)
        self.assertEqual(result['armourRoll']['rawResult'], 12)
        self.assertEqual(result['armourRoll']['modifiedResult'], 13)
        self.assertEqual(result['injuryRoll']['rawResult'], 2)
        self.assertEqual(result['injuryRoll']['modifiedResult'], 2)

    def test_knock_down_mighty_blow_injury(self):
        """
        Test that a modifier is added to the armour roll.
        """
        victim = self.place_player('home', self.xpos, self.ypos, True)
        step = self.create_test_knock_down_step(victim, 'injury')
        with patch('random.randint', RiggedDice((6, 6, 1, 1))):
            result = self.match.resolve(step)
        self.assertEqual(result['armourRoll']['rawResult'], 12)
        self.assertEqual(result['armourRoll']['modifiedResult'], 12)
        self.assertEqual(result['injuryRoll']['rawResult'], 2)
        self.assertEqual(result['injuryRoll']['modifiedResult'], 3)

    def test_stand_up(self):
        """
        Test that a player successfully stands up.
        """
        pig = self.place_player('home', self.xpos, self.ypos)
        pig.down = True
        pig.tackle_zones = False
        pig.save()
        step = self.create_test_stand_up_step(pig)
        result = self.match.resolve(step)
        pig = self.reload_pig(pig)
        self.assertFalse(pig.down)
        self.assertTrue(pig.tackle_zones)
        self.assertTrue(result['success'])

class PickUpTests(BloodBowlTestCase):

    xpos = 15
    ypos = 5

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')
        self.pig = self.place_player('home', self.xpos, self.ypos)
        self.match.x_ball = self.xpos
        self.match.y_ball = self.ypos
        self.match.save()

    def create_test_pick_up_step(self, pig):
        """
        Create a step where the player stands up.
        """
        properties = {
            'action': 'move',
            'num': pig.player.number,
            'side': self.side_of_pig(pig),
        }
        return self.create_test_step('pickUp', 'move', properties)

    @patch('random.randint', RiggedDice((6, )))
    def test_pick_up_success(self):
        """
        Test that the ball is successfully picked up.
        """
        step = self.create_test_pick_up_step(self.pig)
        result = self.match.resolve(step)
        self.pig = self.reload_pig(self.pig)
        self.assertTrue(self.pig.has_ball)
        self.assertTrue(result['success'])
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 1)

    @patch('random.randint', RiggedDice((1, )))
    def test_pick_up_success(self):
        """
        Test that the ball is unsuccessfully picked up.
        """
        step = self.create_test_pick_up_step(self.pig)
        result = self.match.resolve(step)
        self.pig = self.reload_pig(self.pig)
        self.assertFalse(self.pig.has_ball)
        self.assertFalse(result['success'])
        
    @patch('random.randint', RiggedDice((6, )))
    def test_pick_up_tackle_zone(self):
        """
        Test that an opposing player changes the modifier.
        """
        opponent = self.place_player('away', self.xpos+1, self.ypos)
        step = self.create_test_pick_up_step(self.pig)
        result = self.match.resolve(step)
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 0)

class ScatterTests(BloodBowlTestCase):

    xpos = 0
    ypos = 5

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')
        self.match.x_ball = self.xpos
        self.match.y_ball = self.ypos
        self.match.save()

    def create_test_scatter_step(self, n_scatter):
        """
        Create a test step where the ball scatters.
        """
        properties = {
            'action': 'move',
            'x0': str(self.match.x_ball),
            'y0': str(self.match.y_ball),
            'nScatter': str(n_scatter),
        }
        return self.create_test_step('scatter', 'move', properties)

    @patch('random.randint', RiggedDice((3,)))
    def test_scatter_1(self):
        """
        Scatter the ball a single square, on the pitch.
        """
        step = self.create_test_scatter_step(1)
        result = self.match.resolve(step)
        self.reload_match()
        self.assertEqual(self.match.x_ball, self.xpos+1)
        self.assertEqual(self.match.y_ball, self.ypos-1)
        self.assertEqual(result['x1'], self.match.x_ball)
        self.assertEqual(result['y1'], self.match.y_ball)
        self.assertEqual(len(result['dice']['dice']), 1)

    @patch('random.randint', RiggedDice((3, 8, 8)))
    def test_scatter_3(self):
        """
        Scatter the ball three times, still on the pitch.
        """
        step = self.create_test_scatter_step(3)
        result = self.match.resolve(step)
        self.reload_match()
        self.assertEqual(self.match.x_ball, self.xpos+3)
        self.assertEqual(self.match.y_ball, self.ypos+1)
        self.assertEqual(result['x1'], self.match.x_ball)
        self.assertEqual(result['y1'], self.match.y_ball)
        self.assertEqual(len(result['dice']['dice']), 3)

    @patch('random.randint', RiggedDice((2, 1, 1)))
    def test_scatter_off_pitch(self):
        """
        Scatter the ball off the pitch.
        """
        step = self.create_test_scatter_step(3)
        result = self.match.resolve(step)
        self.reload_match()
        self.assertEqual(self.match.x_ball, self.xpos-1)
        self.assertEqual(self.match.y_ball, self.ypos-2)
        self.assertEqual(result['x1'], self.match.x_ball)
        self.assertEqual(result['y1'], self.match.y_ball)
        self.assertEqual(result['lastX'], self.xpos)
        self.assertEqual(result['lastY'], self.ypos-1)
        # Strictly speaking, the third dice roll is unnecessary
        self.assertEqual(len(result['dice']['dice']), 3)

class CatchTests(BloodBowlTestCase):

    xpos = 15
    ypos = 5

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')
        self.catcher = self.place_player('home', self.xpos, self.ypos)
        self.match.x_ball = self.xpos
        self.match.y_ball = self.ypos
        self.match.save()

    def create_test_catch_step(self, pig, accurate):
        """
        Create a test step to try and catch the ball.
        """
        properties = {
            'action': 'pass',
            'num': pig.player.number,
            'side': self.side_of_pig(pig),
            'accurate': accurate,
        }
        return self.create_test_step('catch', 'pass', properties)

    @patch('random.randint', RiggedDice((6,)))
    def test_catch_success_accurate(self):
        """
        Test that the player catches the ball.
        """
        step = self.create_test_catch_step(self.catcher, True)
        result = self.match.resolve(step)
        self.catcher = self.reload_pig(self.catcher)
        self.assertTrue(self.catcher.has_ball)
        self.assertTrue(result['success'])
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 1)

    @patch('random.randint', RiggedDice((6,)))
    def test_catch_success_inaccurate(self):
        """
        Test that the player catches the ball from an inaccurate pass.
        """
        step = self.create_test_catch_step(self.catcher, False)
        result = self.match.resolve(step)
        self.catcher = self.reload_pig(self.catcher)
        self.assertTrue(self.catcher.has_ball)
        self.assertTrue(result['success'])
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 0)

    @patch('random.randint', RiggedDice((1,)))
    def test_catch_failure(self):
        """
        Test that the player fails to catch the ball.
        """
        step = self.create_test_catch_step(self.catcher, True)
        result = self.match.resolve(step)
        self.catcher = self.reload_pig(self.catcher)
        self.assertFalse(self.catcher.has_ball)
        self.assertFalse(result['success'])
        
    @patch('random.randint', RiggedDice((6,)))
    def test_catch_success_tackle_zones(self):
        """
        Test that tackle zones make catching the ball more difficult.
        """
        opponent = self.place_player('away', self.xpos+1, self.ypos)
        step = self.create_test_catch_step(self.catcher, True)
        result = self.match.resolve(step)
        self.catcher = self.reload_pig(self.catcher)
        self.assertTrue(self.catcher.has_ball)
        self.assertTrue(result['success'])
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 0)

    @patch('random.randint', RiggedDice((6,)))
    def test_catch_bone_head(self):
        """
        Test that a player affected by Bone-head always fails.
        """
        self.catcher.add_effect('Bone-head')
        step = self.create_test_catch_step(self.catcher, True)
        result = self.match.resolve(step)
        self.catcher = self.reload_pig(self.catcher)
        self.assertFalse(self.catcher.has_ball)
        self.assertFalse(result['success'])

    @patch('random.randint', RiggedDice((6,)))
    def test_catch_really_stupid(self):
        """
        Test that a player affected by Really Stupid always fails.
        """
        self.catcher.add_effect('Really Stupid')
        step = self.create_test_catch_step(self.catcher, True)
        result = self.match.resolve(step)
        self.catcher = self.reload_pig(self.catcher)
        self.assertFalse(self.catcher.has_ball)
        self.assertFalse(result['success'])

class ThrowTests(BloodBowlTestCase):

    xpos = 0
    ypos = 5

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')
        self.thrower = self.place_player('home', self.xpos, self.ypos, True)
        self.match.x_ball = self.xpos
        self.match.y_ball = self.ypos
        self.match.save()

    def create_test_throw_step(self, pig, x1, y1):
        """
        Create a test step to try and throw the ball.
        """
        properties = {
            'action': 'pass',
            'num': pig.player.number,
            'side': self.side_of_pig(pig),
            'x0': pig.xpos,
            'y0': pig.ypos,
            'x1': x1,
            'y1': y1,
        }
        return self.create_test_step('pass', 'pass', properties)

    def create_test_hand_off_step(self, pig, x1, y1):
        """
        Create a test step to try and hand off the ball.
        """
        properties = {
            'action': 'handOff',
            'num': pig.player.number,
            'side': self.side_of_pig(pig),
            'x0': pig.xpos,
            'y0': pig.ypos,
            'x1': x1,
            'y1': y1,
        }
        return self.create_test_step('handOff', 'handOff', properties)

    @patch('random.randint', RiggedDice((6,)))
    def test_throw_quick_success(self):
        """
        Test throwing a quick pass successfully.
        """
        x1 = self.xpos + 3
        y1 = self.ypos
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        self.assertTrue(result['success'])
        self.assertFalse(result['fumble'])
        self.assertEqual(result['x1'], x1)
        self.assertEqual(result['y1'], y1)
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 1)
        self.assertEqual(self.match.x_ball, x1)
        self.assertEqual(self.match.y_ball, y1)
        self.assertFalse(self.thrower.has_ball)
        self.assertTrue(self.thrower.finished_action)

    @patch('random.randint', RiggedDice((2,)))
    def test_throw_quick_fail(self):
        """
        Test throwing a quick pass unsuccessfully.
        """
        x1 = self.xpos + 3
        y1 = self.ypos
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        self.assertFalse(result['success'])
        self.assertFalse(result['fumble'])
        self.assertEqual(result['x1'], x1)
        self.assertEqual(result['y1'], y1)
        self.assertEqual(self.match.x_ball, x1)
        self.assertEqual(self.match.y_ball, y1)
        self.assertFalse(self.thrower.has_ball)
        self.assertTrue(self.thrower.finished_action)

    @patch('random.randint', RiggedDice((1,)))
    def test_throw_quick_fumble(self):
        """
        Test fumbling a quick pass.
        """
        x1 = self.xpos + 3
        y1 = self.ypos
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        self.assertFalse(result['success'])
        self.assertTrue(result['fumble'])
        self.assertEqual(self.match.x_ball, self.xpos)
        self.assertEqual(self.match.y_ball, self.ypos)
        self.assertFalse(self.thrower.has_ball)
        self.assertTrue(self.thrower.finished_action)

    @patch('random.randint', RiggedDice((6,)))
    def test_throw_quick_tackle_zone(self):
        """
        Test throwing a quick pass successfully.
        """
        x1 = self.xpos + 3
        y1 = self.ypos
        opponent = self.place_player('away', self.xpos+1, self.ypos)
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        self.assertTrue(result['success'])
        self.assertFalse(result['fumble'])
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 0)
        
    @patch('random.randint', RiggedDice((6,)))
    def test_throw_short_success(self):
        """
        Test throwing a short pass successfully.
        """
        x1 = self.xpos + 6
        y1 = self.ypos
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, 0)

    @patch('random.randint', RiggedDice((6,)))
    def test_throw_long_success(self):
        """
        Test throwing a long pass successfully.
        """
        x1 = self.xpos + 10
        y1 = self.ypos
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, -1)

    @patch('random.randint', RiggedDice((6,)))
    def test_throw_long_bomb_success(self):
        """
        Test throwing a quick pass successfully.
        """
        x1 = self.xpos + 13
        y1 = self.ypos
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        modifier = result['modifiedResult'] - result['rawResult']
        self.assertEqual(modifier, -2)

    @patch('random.randint', RiggedDice((2,)))
    def test_throw_long_bomb_fumble(self):
        """
        Test fumbling a long bomb, via a modified <=1.
        """
        x1 = self.xpos + 13
        y1 = self.ypos
        step = self.create_test_throw_step(self.thrower, x1, y1)
        result = self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        self.assertFalse(result['success'])
        self.assertTrue(result['fumble'])
        self.assertEqual(self.match.x_ball, self.xpos)
        self.assertEqual(self.match.y_ball, self.ypos)
        self.assertFalse(self.thrower.has_ball)
        self.assertTrue(self.thrower.finished_action)

    def test_hand_off(self):
        x1 = self.xpos + 1
        y1 = self.ypos + 1
        step = self.create_test_hand_off_step(self.thrower, x1, y1)
        self.match.resolve(step)
        self.reload_match()
        self.thrower = self.reload_pig(self.thrower)
        self.assertEqual(self.match.x_ball, x1)
        self.assertEqual(self.match.y_ball, y1)
        self.assertTrue(self.thrower.finished_action)


class ThrowTests(BloodBowlTestCase):

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')

    def create_test_throwin_step(self, last_x, last_y):
        """
        Create a test throwin step.
        """
        properties = {
            'action': 'pass',
            'lastX': str(last_x),
            'lastY': str(last_y),
        }
        return self.create_test_step('throwin', 'pass', properties)

    @patch('random.randint', RiggedDice((2, 1, 6)))
    def test_throwin_on_pitch(self):
        """
        Test a throwin that lands on the pitch.
        """
        last_x = 1
        last_y = 0
        step = self.create_test_throwin_step(last_x, last_y)
        result = self.match.resolve(step)
        self.reload_match()
        self.assertEqual(self.match.x_ball, last_x)
        self.assertEqual(self.match.y_ball, last_y + 6)
        self.assertEqual(result['x1'], last_x)
        self.assertEqual(result['y1'], last_y + 6)

    @patch('random.randint', RiggedDice((3, 1, 6)))
    def test_throwin_off_pitch(self):
        """
        Test a throwin that lands off the pitch.
        """
        last_x = 1
        last_y = 0
        step = self.create_test_throwin_step(last_x, last_y)
        result = self.match.resolve(step)
        self.reload_match()
        self.assertEqual(self.match.x_ball, last_x - 2)
        self.assertEqual(self.match.y_ball, last_y + 2)
        self.assertEqual(result['x1'], last_x - 2)
        self.assertEqual(result['y1'], last_y + 2)
        self.assertEqual(result['lastX'], last_x - 1)
        self.assertEqual(result['lastY'], last_y + 1)

class GoForItTests(BloodBowlTestCase):

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')

    def create_test_go_for_it_step(self):
        """
        Create a go for it attempt.
        """
        return self.create_test_step('goForIt', 'move', {})

    @patch('random.randint', RiggedDice((2,)))
    def test_go_for_it_success(self):
        """
        Test a successful go for it.
        """
        step = self.create_test_go_for_it_step()
        result = self.match.resolve(step)
        self.assertTrue(result['success'])

    @patch('random.randint', RiggedDice((1,)))
    def test_go_for_it_failure(self):
        """
        Test an unsuccessful go for it.
        """
        step = self.create_test_go_for_it_step()
        result = self.match.resolve(step)
        self.assertFalse(result['success'])


class EndTurnTests(BloodBowlTestCase):

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')
        self.match.first_kicking_team = 'home'
        self.match.turn_type = 'normal'
        self.match.turn_number = 1
        self.match.save()

    def end_turn(self, touchdown_side=None):
        """
        End the current turn.
        """
        if touchdown_side is None:
            properties = {}
        else:
            properties = {
                'touchdown': True,
                'side': touchdown_side,
            }
        step = self.create_test_step('endTurn', 'endTurn', properties)
        self.match.resolve(step)
        self.reload_match()

    def test_end_turn_reroll_used(self):
        """
        Test that rerolls are marked as unused at end of turn.
        """
        self.match.home_reroll_used_this_turn = True
        self.match.away_reroll_used_this_turn = True
        self.match.save()
        self.end_turn()
        self.assertFalse(self.match.home_reroll_used_this_turn)
        self.assertFalse(self.match.away_reroll_used_this_turn)

    def test_end_turn_touchdown(self):
        """
        Test that a touchdown is correctly added to the score.
        """
        self.end_turn('home')
        self.assertEqual(self.match.home_score, 1)
        self.assertEqual(self.match.away_score, 0)
        self.end_turn('away')
        self.assertEqual(self.match.home_score, 1)
        self.assertEqual(self.match.away_score, 1)

    def test_end_turn_turn_number(self):
        """
        Test that the turn number changes appropriately.
        """
        self.match.current_side = other_side(self.match.first_kicking_team)
        self.end_turn()
        self.assertEqual(
            self.match.current_side, self.match.first_kicking_team)
        self.assertEqual(self.match.turn_number, 1)
        self.end_turn()
        self.assertEqual(
            self.match.current_side, other_side(self.match.first_kicking_team))
        self.assertEqual(self.match.turn_number, 2)

    def test_end_turn_end_half(self):
        """
        Test that the half ends appropriately.
        """
        self.match.turn_number = 8
        self.match.current_side = self.match.first_kicking_team
        self.match.home_rerolls = 0
        self.match.away_rerolls = 0
        self.match.save()
        self.end_turn()
        self.assertEqual(self.match.turn_number, 9)
        self.assertEqual(
            self.match.home_rerolls, self.match.home_rerolls_total)
        self.assertEqual(
            self.match.away_rerolls, self.match.away_rerolls_total)

    def test_end_turn_end_match(self):
        """
        Test that the match ends appropriately.
        """
        self.match.turn_number = 16
        self.match.current_side = other_side(self.match.first_kicking_team)
        self.match.save()
        self.end_turn()
        self.assertEqual(self.match.turn_type, 'end')

    def test_end_turn_stunned(self):
        """
        Test that stunned players act correctly at the end of the turn.
        """
        pig_list = [
            self.place_player('home', 0, 0),
            self.place_player('home', 0, 1),
            self.place_player('away', 0, 2),
            self.place_player('away', 0, 3),
        ]
        for idx, pig in enumerate(pig_list):
            pig.down = True
            pig.stunned = True
            pig.stunned_this_turn = (idx == 1 or idx == 3)
            pig.save()
        self.match.current_side = 'home'
        self.match.save()
        self.end_turn()
        for idx, pig in enumerate(pig_list):
            pig_list[idx] = self.reload_pig(pig)
            self.assertTrue(pig_list[idx].down)
            self.assertFalse(pig_list[idx].stunned_this_turn)
        self.assertFalse(pig_list[0].stunned)
        self.assertTrue(pig_list[1].stunned)
        self.assertTrue(pig_list[2].stunned)
        self.assertTrue(pig_list[3].stunned)

    def test_end_turn_players(self):
        """
        Test that players are reset at the start of each turn.
        """
        pig_list = [
            self.place_player('home', 0, 0),
            self.place_player('away', 0, 1),
        ]
        for pig in pig_list:
            pig.move_left = 1
            pig.action = 'move'
            pig.finished_action = True
            pig.save()
        self.end_turn()
        for pig in pig_list:
            pig = self.reload_pig(pig)
            self.assertEqual(pig.move_left, pig.ma)
            self.assertEqual(pig.action, '')
            self.assertFalse(pig.finished_action)


class KickoffTests(BloodBowlTestCase):

    def setUp(self):
        """
        Create a suitable match.
        """
        self.match = create_test_match('human', 'orc')

    def create_test_set_kickoff_step(self, kicking_team):
        """
        Create a test kickoff step.
        """
        properties = {
            'action': 'setKickoff',
            'kickingTeam': kicking_team,
        }
        return self.create_test_step(
            'setKickoff', 'setKickoff', properties=properties)

    def set_kickoff(self, kicking_team):
        """
        Set a kickoff.
        """
        step = self.create_test_set_kickoff_step(kicking_team)
        result = self.match.resolve(step)
        self.reload_match()
        return result

    def test_set_kickoff(self):
        """
        Test that everything is reset correctly for the kickoff.
        """
        for num, side in product(range(1, 12), ('home', 'away')):
            pig = PlayerInGame.objects.get(
                match=self.match, player__number=num,
                player__team=self.match.team(side))
            pig.xpos = num
            if side == 'away':
                pig.xpos += 11
            pig.down = True
            pig.stunned = True
            pig.stunned_this_turn = True
            pig.tackle_zones = False
            pig.move_left = 0
            pig.action = 'move'
            pig.finished_action = True
            pig.save()
        pig.has_ball = True
        pig.save()
        self.set_kickoff('home')
        for pig in PlayerInGame.objects.filter(match=self.match):
            self.assertFalse(pig.down)
            self.assertFalse(pig.stunned)
            self.assertFalse(pig.stunned_this_turn)
            self.assertTrue(pig.tackle_zones)
            self.assertFalse(pig.has_ball)
            self.assertEqual(pig.move_left, pig.ma)
            self.assertEqual(pig.action, '')
            self.assertFalse(pig.finished_action)
        self.assertEqual(self.match.n_to_place, 2)
        self.assertEqual(self.match.kicking_team, 'home')
        self.assertEqual(self.match.current_side, 'home')
        self.assertIsNone(self.match.x_ball)
        self.assertIsNone(self.match.y_ball)
        self.assertEqual(self.match.turn_type, 'placePlayers')

    @patch('random.randint', RiggedDice((3, 4, 3, 4)))
    def test_set_kickoff_reviving(self):
        """
        Test that some players are revived when kicking off.
        """
        for pig in PlayerInGame.objects.filter(
                match=self.match, player__number__lt=3):
            pig.knocked_out = True
            pig.save()
        result = self.set_kickoff('home')
        self.assertEqual(len(result['revived']), 2)
        self.assertEqual(len(result['knockedOut']), 2)
        for player_data in result['revived']:
            pig = PlayerInGame.objects.get(
                match=self.match, player__number=player_data['num'],
                player__team=self.match.team(player_data['side']))
            self.assertFalse(pig.knocked_out)
        for player_data in result['knockedOut']:
            pig = PlayerInGame.objects.get(
                match=self.match, player__number=player_data['num'],
                player__team=self.match.team(player_data['side']))
            self.assertTrue(pig.knocked_out)



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

