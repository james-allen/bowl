import json
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User

from game.models import Race, Team, Player, PlayerInGame, Step, Position, Match
from game.models import start_match, create_team, create_player
from game.define_teams import define_all

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
                'dodge': 'true',
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

