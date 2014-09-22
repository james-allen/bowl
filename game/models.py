import json
import re
from collections import defaultdict

from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

from game.utils import roll_dice, roll_agility_dice, roll_injury_dice
from game.utils import roll_armour_dice, roll_block_dice, is_double
from game.utils import on_pitch, find_pass_range, other_side, add_next_step


class Race(models.Model):
    singular = models.CharField(max_length=50)
    plural = models.CharField(max_length=50)
    reroll_cost = models.IntegerField()

    def __str__(self):
        return self.singular


class Team(models.Model):
    name = models.CharField(max_length=100)
    race = models.ForeignKey(Race)
    value = models.IntegerField(default=0)
    rerolls = models.IntegerField(default=0)
    cash = models.IntegerField(default=0)
    coach = models.ForeignKey(User)
    slug = models.SlugField(unique=True)
    color_home_primary = models.CharField(max_length=11)
    color_home_secondary = models.CharField(max_length=11)
    color_away_primary = models.CharField(max_length=11)
    color_away_secondary = models.CharField(max_length=11)

    def __str__(self):
        return self.slug

    def update_value(self):
        """Recalculate the value of the team."""
        value = 0
        for player in self.player_set.all():
            value += player.value
        value += self.rerolls * self.race.reroll_cost
        value += self.cash
        self.value = value
        self.save()
        return

    def valid_starting_team(self):
        """Return True if this is a valid starting team."""
        if self.player_set.count() < 11:
            return False
        if self.cash < 0:
            return False
        if self.value != 1000:
            return False
        if (self.color_home_primary == self.color_away_primary or
                self.color_home_primary == self.color_home_secondary or
                self.color_away_primary == self.color_away_secondary):
            return False
        if self.name == '':
            return False
        name_list = []
        position_tally = defaultdict(int)
        for player in self.player_set.all():
            if player.name == '':
                return False
            if player.name in name_list:
                return False
            name_list.append(player.name)
            position_tally[player.position.title] += 1
            if (position_tally[player.position.title] > 
                    player.position.max_quantity):
                return False

        return True

def create_team(name, race, coach, **kwargs):
    team = Team(name=name, race=race, coach=coach, **kwargs)
    slug = slugify(name)
    try:
        Team.objects.get(slug=slug)
    except Team.DoesNotExist:
        pass
    else:
        i = 1
        while True:
            try:
                slug = slugify(name) + '-' + str(i)
                Team.objects.get(slug=slug)
            except Team.DoesNotExist:
                break
            else:
                i += 1
    team.slug = slug
    return team


class Challenge(models.Model):
    challenger = models.ForeignKey(Team, related_name='challenges_issued')
    challengee = models.ForeignKey(Team, related_name='challenges_received')
    time_issued = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.challenger.slug + ' vs ' + self.challengee.slug


class Position(models.Model):
    title = models.CharField(max_length=30)
    team_race = models.ForeignKey(Race)
    race = models.CharField(max_length=50)
    max_quantity = models.IntegerField()
    cost = models.IntegerField()
    ma = models.IntegerField()
    st = models.IntegerField()
    ag = models.IntegerField()
    av = models.IntegerField()
    skills = models.TextField()
    normal_skills = models.CharField(max_length=5)
    double_skills = models.CharField(max_length=5)

    def __str__(self):
        return self.team_race.singular + ' ' + self.title


class Player(models.Model):
    name = models.CharField(max_length=100)
    race = models.CharField(max_length=50)
    team = models.ForeignKey(Team)
    position = models.ForeignKey(Position)
    number = models.IntegerField()
    value = models.IntegerField()
    ma = models.IntegerField()
    st = models.IntegerField()
    ag = models.IntegerField()
    av = models.IntegerField()
    skills = models.TextField()
    normal_skills = models.CharField(max_length=5)
    double_skills = models.CharField(max_length=5)
    games = models.IntegerField(default=0)
    spps = models.IntegerField(default=0)
    completions = models.IntegerField(default=0)
    casualties = models.IntegerField(default=0)
    interceptions = models.IntegerField(default=0)
    touchdowns = models.IntegerField(default=0)
    mvps = models.IntegerField(default=0)
    niggles = models.IntegerField(default=0)
    dead = models.BooleanField(default=False)

    def __str__(self):
        return self.name

def create_player(team, position_title, name, number):
    position = Position.objects.get(
        title=position_title, team_race=team.race)
    player = Player(
        name=name,
        race=position.race,
        team=team,
        position=position,
        number=number,
        value=position.cost,
        ma=position.ma,
        st=position.st,
        ag=position.ag,
        av=position.av,
        skills=position.skills,
        normal_skills=position.normal_skills,
        double_skills=position.double_skills,
        )
    return player


class Match(models.Model):
    home_team = models.ForeignKey(Team, related_name='home_match')
    away_team = models.ForeignKey(Team, related_name='away_match')
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    turn_number = models.IntegerField(default=1)
    turn_type = models.CharField(max_length=12, default='placePlayers')
    current_side = models.CharField(max_length=4)
    first_kicking_team = models.CharField(max_length=4)
    home_first_direction = models.CharField(max_length=5)
    x_ball = models.IntegerField(null=True, default=None)
    y_ball = models.IntegerField(null=True, default=None)
    home_rerolls = models.IntegerField(default=0)
    away_rerolls = models.IntegerField(default=0)
    home_rerolls_total = models.IntegerField(default=0)
    away_rerolls_total = models.IntegerField(default=0)
    home_reroll_used_this_turn = models.BooleanField(default=False)
    away_reroll_used_this_turn = models.BooleanField(default=False)
    n_to_place = models.IntegerField(default=0)
    kicking_team = models.CharField(max_length=4)

    def __str__(self):
        return self.home_team.slug + ' vs ' + self.away_team.slug

    def as_dict(self):
        result_dict = {
            'id': self.id,
            'homeTeam': self.home_team.name,
            'awayTeam': self.away_team.name,
            'homeCoach': self.home_team.coach.username,
            'awayCoach': self.away_team.coach.username,
            'homeScore': self.home_score,
            'awayScore': self.away_score,
            'turnNumber': self.turn_number,
            'turnType': self.turn_type,
            'currentSide': self.current_side,
            'firstKickingTeam': self.first_kicking_team,
            'homeFirstDirection': self.home_first_direction,
            'xBall': self.x_ball,
            'yBall': self.y_ball,
            'homeRerolls': self.home_rerolls,
            'awayRerolls': self.away_rerolls,
            'homeRerollsTotal': self.home_rerolls_total,
            'awayRerollsTotal': self.away_rerolls_total,
            'homeRerollUsedThisTurn': self.home_reroll_used_this_turn,
            'awayRerollUsedThisTurn': self.away_reroll_used_this_turn,
            'nToPlace': self.n_to_place,
            'kickingTeam': self.kicking_team,
        }
        return result_dict

    def team(self, side):
        if side == 'home':
            return self.home_team
        elif side == 'away':
            return self.away_team
        else:
            raise ValueError('Unrecognised side: ' + side)

    def side(self, team):
        if team == self.home_team:
            return 'home'
        elif team == self.away_team:
            return 'away'
        else:
            raise ValueError('Unrecognised team: ' + repr(team))

    def find_player(self, side, num):
        """Return a PlayerInGame object."""
        return PlayerInGame.objects.get(
            match=self, player__team=self.team(side), player__number=int(num))

    def finish_previous_action(self, current_player):
        active_steps = ('move', 'block', 'standUp', 'pass', 'foul', 'handOff')
        step_set = Step.objects.filter(match=self).order_by('-history_position')
        for step in step_set:
            if step is step_set[0]:
                continue
            if step.step_type == 'endTurn':
                return
            if step.step_type in active_steps:
                player = step.player()
                if (player.side == current_player.side and 
                        player.player.number == current_player.player.number):
                    continue
                player.finished_action = True
                player.save()

    def resolve(self, step):
        """Resolve a step."""
        step_type = step.step_type
        result = {}
        if step_type == 'reroll':
            data = step.properties_dict()
            if data['rerollType'] == 'team':
                if data['side'] == 'home':
                    self.home_rerolls -= 1
                    self.home_reroll_used_this_turn = True
                else:
                    self.away_rerolls -= 1
                    self.away_reroll_used_this_turn = True
                self.save()
            player = step.player()
            if player.has_skill('Loner'):
                loner_dice = roll_dice(6, 1)
                loner_success = loner_dice['dice'][0] >= 4
                loner_dict = {'dice': loner_dice, 'success': loner_success}
                result.update({'loner': loner_dict})
                if not loner_success:
                    # Copy the results of the last attempt and return now
                    result.update(step.previous().as_dict()['result'])
                    return result
            step_type = data['rerollStepType']
        if step_type == 'move':
            return self.resolve_move(step, result)
        elif step_type == 'push':
            return self.resolve_push(step, result)
        elif step_type == 'followUp':
            return self.resolve_follow_up(step, result)
        elif step_type == 'block':
            return self.resolve_block(step, result)
        elif step_type == 'selectBlockDice':
            return self.resolve_select_block_dice(step, result)
        elif step_type == 'foul':
            return self.resolve_foul(step, result)
        elif step_type == 'knockDown':
            return self.resolve_knock_down(step, result)
        elif step_type == 'standUp':
            return self.resolve_stand_up(step, result)
        elif step_type == 'pickUp':
            return self.resolve_pick_up(step, result)
        elif step_type == 'scatter':
            return self.resolve_scatter(step, result)
        elif step_type == 'catch':
            return self.resolve_catch(step, result)
        elif step_type == 'pass':
            return self.resolve_pass(step, result)
        elif step_type == 'handOff':
            return self.resolve_hand_off(step, result)
        elif step_type == 'throwin':
            return self.resolve_throwin(step, result)
        elif step_type == 'goForIt':
            return self.resolve_go_for_it(step, result)
        elif step_type == 'endTurn':
            return self.resolve_end_turn(step, result)
        elif step_type == 'setKickoff':
            return self.resolve_set_kickoff(step, result)
        elif step_type == 'placeBall':
            return self.resolve_place_ball(step, result)
        elif step_type == 'placePlayer':
            return self.resolve_place_player(step, result)
        elif step_type == 'submitPlayers':
            return self.resolve_submit_players(step, result)
        elif step_type == 'submitBall':
            return self.resolve_submit_ball(step, result)
        elif step_type == 'touchback':
            return self.resolve_touchback(step, result)
        elif step_type == 'submitTouchback' or step_type == 'endKickoff':
            return self.resolve_end_kickoff(step, result)
        elif step_type == 'bonehead':
            return self.resolve_bonehead(step, result)
        elif step_type == 'reallyStupid':
            return self.resolve_really_stupid(step, result)

    def resolve_move(self, step, result):
        """Resolve a move step."""
        data = step.properties_dict()
        player = step.player()
        player.set_action(data['action'])
        # Update the player's position in the database
        player.xpos = int(data['x1'])
        player.ypos = int(data['y1'])
        player.move_left -= 1
        if player.move_left == -2 and (
                player.action == 'move' or player.action == 'blitz'):
            player.finished_action = True
        if player.has_ball:
            # Move the ball too
            self.x_ball = int(data['x1'])
            self.y_ball = int(data['y1'])
            self.save()
        if data['dodge']:
            modifier = 1 - player.n_tackle_zones()
            result.update(roll_agility_dice(player, modifier=modifier))
        else:
            # Not sure if this is necessary
            result.update({'success': True})
        player.save()
        return result

    def resolve_push(self, step, result):
        """Resolve a push step."""
        data = step.properties_dict()
        player = step.player()
        # Update the player's position in the database
        player.xpos = int(data['x1'])
        player.ypos = int(data['y1'])
        if player.has_ball:
            # Move the ball too
            self.x_ball = int(data['x1'])
            self.y_ball = int(data['y1'])
            self.save()
        if data['offPitch']:
            player.on_pitch = False
            injury_roll = roll_injury_dice(player)
            if injury_roll['result'] == 'knockedOut':
                player.knocked_out = True
            elif injury_roll['result'] == 'casualty':
                player.casualty = True
            result.update({'injuryRoll': injury_roll})
        player.save()
        return result

    def resolve_follow_up(self, step, result):
        """Resolve a follow-up."""
        data = step.properties_dict()
        if data['choice']:
            player = step.player()
            # Update the player's position in the database
            player.xpos = int(data['x1'])
            player.ypos = int(data['y1'])
            if player.has_ball:
                # Move the ball too
                self.x_ball = int(data['x1'])
                self.y_ball = int(data['y1'])
                self.save()
            player.save()
        return result

    def resolve_block(self, step, result):
        """Resolve a block step."""
        data = step.properties_dict()
        # Find out which is the attacking player
        if data['side'] == 'home':
            attacking_team = self.home_team
            defending_team = self.away_team
        elif data['side'] == 'away':
            attacking_team = self.away_team
            defending_team = self.home_team
        attacking_num = int(data['num'])
        defending_num = int(data['targetNum'])
        attacking_player = PlayerInGame.objects.get(
            match=self, player__team=attacking_team, 
            player__number=attacking_num)
        attacking_player.set_action(data['action'])
        defending_player = PlayerInGame.objects.get(
            match=self, player__team=defending_team,
            player__number=defending_num)
        attack_st = attacking_player.player.st
        result['rawAttackSt'] = attack_st
        for player in PlayerInGame.objects.filter(
            match=self, player__team=attacking_team,
            xpos__gt=(defending_player.xpos-2),
            xpos__lt=(defending_player.xpos+2),
            ypos__gt=(defending_player.ypos-2),
            ypos__lt=(defending_player.ypos+2),
            on_pitch=True, down=False, tackle_zones=True):
            if (player != attacking_player and 
                    player.n_tackle_zones(exclude=defending_player) == 0):
                attack_st += 1
        defence_st = defending_player.player.st
        result['rawDefenceSt'] = defence_st
        for player in PlayerInGame.objects.filter(
            match=self, player__team=defending_team,
            xpos__gt=(attacking_player.xpos-2),
            xpos__lt=(attacking_player.xpos+2),
            ypos__gt=(attacking_player.ypos-2),
            ypos__lt=(attacking_player.ypos+2),
            on_pitch=True, down=False, tackle_zones=True):
            if (player != defending_player and 
                    player.n_tackle_zones(exclude=attacking_player) == 0):
                defence_st += 1
        n_dice = 1
        if attack_st > (2 * defence_st):
            n_dice = 3
        elif attack_st > defence_st:
            n_dice = 2
        elif (2 * attack_st) < defence_st:
            n_dice = 3
        elif attack_st < defence_st:
            n_dice = 2
        result.update(roll_block_dice(n_dice))
        result['attackSt'] = attack_st
        result['defenceSt'] = defence_st
        if data['action'] == 'blitz':
            attacking_player.move_left -= 1
        if attacking_player.move_left == -2 or data['action'] != "blitz":
            attacking_player.finished_action = True
        attacking_player.save()
        return result

    def resolve_select_block_dice(self, step, result):
        """Resolve a block dice being selected."""
        data = step.properties_dict()
        attacker = self.find_player(data['side'], data['num'])
        defender = self.find_player(data['targetSide'], data['targetNum'])
        if data['selectedDice'] == 'attackerDown':
            add_next_step(result, self.define_knock_down(data, 'attacker'))
        elif data['selectedDice'] == 'bothDown':
            if not defender.has_skill('Block'):
                add_next_step(result, self.define_knock_down(data, 'defender'))
            if not attacker.has_skill('Block'):
                add_next_step(result, self.define_knock_down(data, 'attacker'))
        elif data['selectedDice'] == 'pushed':
            add_next_step(result, self.define_push(data))
            add_next_step(result, self.define_follow_up(data))
        elif data['selectedDice'] == 'defenderStumbles':
            add_next_step(result, self.define_push(data))
            add_next_step(result, self.define_follow_up(data))
            if not defender.has_skill('Dodge'):
                add_next_step(result, self.define_knock_down(data, 'defender'))
        elif data['selectedDice'] == 'defenderDown':
            add_next_step(result, self.define_push(data))
            add_next_step(result, self.define_follow_up(data))
            add_next_step(result, self.define_knock_down(data, 'defender'))            
        return result

    def resolve_foul(self, step, result):
        """Resolve a foul on a player."""
        data = step.properties_dict()
        # Find out which is the attacking player
        if data['side'] == 'home':
            attacking_team = self.home_team
            defending_team = self.away_team
        elif data['side'] == 'away':
            attacking_team = self.away_team
            defending_team = self.home_team
        attacking_num = int(data['num'])
        defending_num = int(data['targetNum'])
        attacking_player = PlayerInGame.objects.get(
            match=self, player__team=attacking_team, 
            player__number=attacking_num)
        attacking_player.set_action(data['action'])
        defending_player = PlayerInGame.objects.get(
            match=self, player__team=defending_team,
            player__number=defending_num)
        modifier = 0
        for player in PlayerInGame.objects.filter(
            match=self, player__team=attacking_team,
            xpos__gt=(defending_player.xpos-2),
            xpos__lt=(defending_player.xpos+2),
            ypos__gt=(defending_player.ypos-2),
            ypos__lt=(defending_player.ypos+2),
            on_pitch=True, down=False, tackle_zones=True):
            if player != attacking_player and player.n_tackle_zones() == 0:
                modifier += 1
        for player in PlayerInGame.objects.filter(
            match=self, player__team=defending_team,
            xpos__gt=(attacking_player.xpos-2),
            xpos__lt=(attacking_player.xpos+2),
            ypos__gt=(attacking_player.ypos-2),
            ypos__lt=(attacking_player.ypos+2),
            on_pitch=True, down=False, tackle_zones=True):
            if (player != defending_player and
                    player.n_tackle_zones(exclude=attacking_player) == 0):
                modifier -= 1
        # Roll against armour
        armour_roll = roll_armour_dice(defending_player, modifier)
        if armour_roll['success']:
            injury_roll = roll_injury_dice(defending_player)
            if injury_roll['result'] == 'stunned':
                defending_player.stunned = True
                defending_player.stunned_this_turn = True
            elif injury_roll['result'] == 'knockedOut':
                defending_player.knocked_out = True
                defending_player.on_pitch = False
            elif injury_roll['result'] == 'casualty':
                defending_player.casualty = True
                defending_player.on_pitch = False
            else:
                raise ValueError('Injury roll returned unexpected result: '+ 
                                 injury_roll['result'])
            defending_player.save()
        else:
            injury_roll = None
        sent_off = (is_double(armour_roll['dice']) or 
                    (armour_roll['success'] and 
                     is_double(injury_roll['dice'])))
        if sent_off:
            attacking_player.sent_off = True
            attacking_player.on_pitch = False
        attacking_player.finished_action = True    
        attacking_player.save()
        result.update({'armourRoll': armour_roll, 'injuryRoll': injury_roll, 
                       'sentOff': sent_off})
        return result

    def resolve_knock_down(self, step, result):
        """Resolve a player being knocked over."""
        data = step.properties_dict()
        player = step.player()
        # Knock the player over in the database
        player.down = True
        player.tackle_zones = False
        player.has_ball = False
        player.save()
        # Check for Mighty Blow skill
        mighty_blow = data.get('mightyBlow', False)
        # Roll against armour
        modifier = 1 if mighty_blow == 'armour' else 0
        armour_roll = roll_armour_dice(player, modifier=modifier)
        if armour_roll['success']:
            modifier = 1 if mighty_blow == 'injury' else 0
            injury_roll = roll_injury_dice(player, modifier=modifier)
            if injury_roll['result'] == 'stunned':
                player.stunned = True
                player.stunned_this_turn = True
            elif injury_roll['result'] == 'knockedOut':
                player.knocked_out = True
                player.on_pitch = False
            elif injury_roll['result'] == 'casualty':
                player.casualty = True
                player.on_pitch = False
            else:
                raise ValueError('Injury roll returned unexpected result: '+
                                 injury_roll['result'])
            player.save()
        else:
            injury_roll = None
        result.update({'armourRoll': armour_roll,
                       'injuryRoll': injury_roll})
        return result

    def resolve_stand_up(self, step, result):
        """Resolve a player standing up."""
        data = step.properties_dict()
        player = step.player()
        player.set_action(data['action'])
        player.move_left -= 3
        if player.move_left <= -2:
            player.finished_action = True
        if player.player.ma < 3:
            dice = roll_dice(6, 1)
            success = dice['dice'][0] >= 4
        else:
            dice = None
            success = True
        if success:
            player.down = False
            player.tackle_zones = True
        player.save()
        result.update({'dice': dice, 'success': success})
        return result

    def resolve_pick_up(self, step, result):
        """Resolve a player picking up the ball."""
        player = step.player()
        modifier = 1 - player.n_tackle_zones()
        result.update(roll_agility_dice(player, modifier=modifier))
        if result['success']:
            player.has_ball = True
            player.save()
        return result

    def resolve_scatter(self, step, result):
        """Resolve the ball scattering."""
        data = step.properties_dict()
        n_scatter = int(data['nScatter'])
        dice = roll_dice(8, n_scatter)
        x_ball = int(data['x0'])
        y_ball = int(data['y0'])
        for direction in dice['dice']:
            last_x = x_ball
            last_y = y_ball
            if direction in [1, 4, 6]:
                x_ball -= 1
            elif direction in [3, 5, 8]:
                x_ball += 1
            if direction in [1, 2, 3]:
                y_ball -= 1
            elif direction in [6, 7, 8]:
                y_ball += 1
            if not on_pitch(x_ball, y_ball):
                break
        self.x_ball = x_ball
        self.y_ball = y_ball
        self.save()
        result.update({'dice': dice, 'direction': direction, 
                       'x1': x_ball, 'y1': y_ball,
                       'lastX': last_x, 'lastY': last_y})
        return result

    def resolve_catch(self, step, result):
        """Resolve a player catching the ball."""
        data = step.properties_dict()
        player = step.player()
        if (player.down or player.affected('Bone-head') or 
                player.affected('Really Stupid')):
            return {'success': False}
        modifier = - player.n_tackle_zones()
        if data['accurate']:
            modifier += 1
        result.update(roll_agility_dice(player, modifier=modifier))
        if result['success']:
            player.has_ball = True
            player.save()
        return result

    def resolve_pass(self, step, result):
        """Resolve passing the ball."""
        data = step.properties_dict()
        player = step.player()
        player.set_action(data['action'])
        delta_x = abs(int(data['x1']) - int(data['x0']))
        delta_y = abs(int(data['y1']) - int(data['y0']))
        pass_range = find_pass_range(delta_x, delta_y)
        if pass_range == 'quickPass':
            modifier = 1
        elif pass_range == 'shortPass':
            modifier = 0
        elif pass_range == 'longPass':
            modifier = -1
        elif pass_range == 'longBomb':
            modifier = -2
        modifier -= player.n_tackle_zones()
        result.update(roll_agility_dice(player, modifier=modifier))
        fumble = (min(result['rawResult'], result['modifiedResult']) <= 1)
        if fumble:
            result['success'] = False
        else:
            self.x_ball = int(data['x1'])
            self.y_ball = int(data['y1'])
            self.save()
            result['x1'] = self.x_ball
            result['y1'] = self.y_ball
        result['fumble'] = fumble
        player.has_ball = False
        player.finished_action = True
        player.save()
        return result

    def resolve_hand_off(self, step, result):
        """Resolve a player handing off the ball to an adjacent player."""
        # Always successful
        data = step.properties_dict()
        player = step.player()
        player.set_action(data['action'])
        player.finished_action = True
        player.save()
        self.x_ball = int(data['x1'])
        self.y_ball = int(data['y1'])
        self.save()
        return result

    def resolve_throwin(self, step, result):
        """Resolve a throwin by the crowd."""
        data = step.properties_dict()
        x0 = int(data['lastX'])
        y0 = int(data['lastY'])
        if y0 == 0:
            edge = 0
        elif y0 == 14:
            edge = 2
        elif x0 == 0:
            edge = 3
        elif x0 == 25:
            edge = 1
        else:
            raise ValueError(
                'Starting coordinates are not on the edge of the pitch!')
        direction_dice = roll_dice(3, 1)
        direction = direction_dice['dice'][0]
        distance_dice = roll_dice(6, 2)
        distance = sum(distance_dice['dice'])
        compass = direction + 2 * edge - 1
        if compass == 0:
            x_dir, y_dir = 1, 1
        elif compass == 1:
            x_dir, y_dir = 0, 1
        elif compass == 2:
            x_dir, y_dir = -1, 1
        elif compass == 3:
            x_dir, y_dir = -1, 0
        elif compass == 4:
            x_dir, y_dir = -1, -1
        elif compass == 5:
            x_dir, y_dir = 0, -1
        elif compass == 6:
            x_dir, y_dir = 1, -1
        elif compass == 7:
            x_dir, y_dir = 1, 0
        x1 = x0 + (distance - 1) * x_dir
        y1 = y0 + (distance - 1) * y_dir
        last_x = x1 - x_dir
        last_y = y1 - y_dir
        while not on_pitch(last_x, last_y):
            x1 = last_x
            y1 = last_y
            last_x = x1 - x_dir
            last_y = y1 - y_dir
        self.x_ball = x1
        self.y_ball = y1
        self.save()
        result.update({'x1': x1, 'y1': y1,
                       'lastX': last_x, 'lastY': last_y})
        return result

    def resolve_go_for_it(self, step, result):
        """Resolve a player going for it."""
        result.update(roll_dice(6, 1))
        result['success'] = (result['dice'][0] != 1)
        return result

    def resolve_end_turn(self, step, result):
        """Resolve the end of a player's turn."""
        data = step.properties_dict()
        for player in PlayerInGame.objects.filter(match=self):
            player.move_left = player.ma
            player.action = ''
            player.finished_action = False
            if (player.player.team == self.team(self.current_side)
                    and player.stunned and not player.stunned_this_turn):
                player.stunned = False
            player.stunned_this_turn = False
            player.save()
        self.home_reroll_used_this_turn = False
        self.away_reroll_used_this_turn = False
        skip_turn = False
        kicking_team = None
        if 'touchdown' in data and data['touchdown']:
            if data['side'] == 'home':
                self.home_score += 1
            else:
                self.away_score += 1
            if data['side'] != self.current_side:
                skip_turn = True
            self.current_side = data['side']
            kicking_team = data['side']
        else:
            self.current_side = other_side(self.current_side)
        next_turn_number = (
            (self.current_side != self.first_kicking_team and 
             self.turn_number <= 8) or
            (self.current_side == self.first_kicking_team and
             self.turn_number >= 9) or
            skip_turn)
        end_of_half = False
        end_of_match = False
        if next_turn_number:
            self.turn_number += 1
            if self.turn_number == 9:
                self.home_rerolls = self.home_rerolls_total
                self.away_rerolls = self.away_rerolls_total
                end_of_half = True
                kicking_team = other_side(self.first_kicking_team)
            if self.turn_number == 17:
                self.turn_type = 'end'
                end_of_match = True
                kicking_team = None
        if kicking_team is not None:
            revive_result = {'revived': [], 'knockedOut': []}
            for player in PlayerInGame.objects.filter(
                    match=self, knocked_out=True):
                dice = roll_dice(6, 1)
                player_data = {'side': player.side, 'num': player.player.number,
                               'dice': dice}
                if dice['dice'][0] >= 4:
                    revive_result['revived'].append(player_data)
                    player.knocked_out = False
                    player.save()
                else:
                    revive_result['knockedOut'].append(player_data)
            set_kickoff(self, kicking_team)
            result.update(revive_result)
        result['nextTurnNumber'] = next_turn_number
        result['kickingTeam'] = kicking_team
        result['endOfHalf'] = end_of_half
        result['endOfMatch'] = end_of_match
        self.save()
        return result

    def resolve_set_kickoff(self, step, result):
        """Resolve setting up a new kickoff."""
        data = step.properties_dict()
        revive_result = {'revived': [], 'knockedOut': []}
        for player in PlayerInGame.objects.filter(
                match=self, knocked_out=True):
            dice = roll_dice(6, 1)
            player_data = {'side': player.side, 'num': player.player.number,
                           'dice': dice}
            if dice['dice'][0] >= 4:
                revive_result['revived'].append(player_data)
                player.knocked_out = False
                player.save()
            else:
                revive_result['knockedOut'].append(player_data)
        set_kickoff(self, data['kickingTeam'])
        self.save()
        result.update(revive_result)
        return result

    def resolve_place_ball(self, step, result):
        """Resolve placing the ball during kickoff."""
        data = step.properties_dict()
        self.x_ball = int(data['x1'])
        self.y_ball = int(data['y1'])
        self.save()
        return result

    def resolve_place_player(self, step, result):
        """Resolve placing a player during kickoff."""
        data = step.properties_dict()
        player = step.player()
        if 'subs' in data and data['subs']:
            player.on_pitch = False
        else:
            player.xpos = int(data['x1'])
            player.ypos = int(data['y1'])
            player.on_pitch = True
        player.save()
        return result

    def resolve_submit_players(self, step, result):
        """Resolve submitting the final player positions during kickoff."""
        self.n_to_place -= 1
        if self.n_to_place == 0:
            self.turn_type = 'placeBall'
        self.current_side = other_side(self.current_side)
        self.save()
        return result

    def resolve_submit_ball(self, step, result):
        """Resolve submitting the final ball position during kickoff."""
        distance_dice = roll_dice(6, 1)
        distance = distance_dice['dice'][0]
        direction_dice = roll_dice(8, 1)
        direction = direction_dice['dice'][0]
        x_ball = self.x_ball
        y_ball = self.y_ball
        if direction in [1, 4, 6]:
            x_ball -= distance
        elif direction in [3, 5, 8]:
            x_ball += distance
        if direction in [1, 2, 3]:
            y_ball -= distance
        elif direction in [6, 7, 8]:
            y_ball += distance
        if not on_pitch(x_ball, y_ball):
            self.x_ball = None
            self.y_ball = None
            self.turn_type = 'touchback'
            self.current_side = other_side(self.current_side)
        else:
            self.x_ball = x_ball
            self.y_ball = y_ball
        self.save()
        result.update({'dice': direction_dice, 'direction': direction, 
                       'distanceDice': distance_dice, 'distance': distance,
                       'x1': x_ball, 'y1': y_ball})
        return result

    def resolve_touchback(self, step, result):
        """Resolve placing the ball during a touchback."""
        data = step.properties_dict()
        self.x_ball = int(data['x1'])
        self.y_ball = int(data['y1'])
        self.save()
        for player in self.playeringame_set.all():
            player.has_ball = False
            player.save()
        player = step.player()
        player.has_ball = True
        player.save()
        return result

    def resolve_end_kickoff(self, step, result):
        """Resolve the end of a kickoff."""
        data = step.properties_dict()
        self.turn_type = 'normal'
        if 'touchback' in data and data['touchback']:
            self.current_side = other_side(self.current_side)
        self.save()
        return result

    def resolve_bonehead(self, step, result):
        """Resolve a bonehead throw."""
        data = step.properties_dict()
        player = step.player()
        player.set_action(data['action'])
        result.update(roll_dice(6, 1))
        result['success'] = (result['dice'][0] != 1)
        if result['success']:
            player.tackle_zones = True
            player.remove_effect('Bone-head')
        else:
            player.tackle_zones = False
            player.add_effect('Bone-head')
            player.finished_action = True
        player.save()
        return result

    def resolve_really_stupid(self, step, result):
        """Resolve a really stupid throw."""
        data = step.properties_dict()
        player = step.player()
        player.set_action(data['action'])
        result.update(roll_dice(6, 1))
        n_helpers = PlayerInGame.objects.filter(
            match=self, player__team=player.team,
            xpos__gt=(player.xpos-2),
            xpos__lt=(player.xpos+2),
            ypos__gt=(player.ypos-2),
            ypos__lt=(player.ypos+2),
            on_pitch=True, down=False).count() - 1
        if n_helpers > 0:
            required_result = 2
        else:
            required_result = 4
        result['success'] = result['dice'][0] >= required_result
        result['requiredResult'] = required_result
        if result['success']:
            player.tackle_zones = True
            player.remove_effect('Really Stupid')
        else:
            player.tackle_zones = False
            player.add_effect('Really Stupid')
            player.finished_action = True
        player.save()
        return result

    def define_knock_down(self, data, victim):
        """Define a knockDown dict."""
        attacker = self.find_player(data['side'], data['num'])
        defender = self.find_player(data['targetSide'], data['targetNum'])
        if victim == 'attacker':
            player = attacker
            perpetrator = defender
        else:
            player = defender
            perpetrator = attacker
        if perpetrator.has_skill('Mighty Blow'):
            if perpetrator == defender:
                mighty_blow = 'armour'
            else:
                mighty_blow = True
        else:
            mighty_blow = False
        new_step = {
            'action': data['action'],
            'stepType': 'knockDown',
            'waitForServer': True,
            'num': player.player.number,
            'side': self.side(player.player.team),
            'perpNum': perpetrator.player.number,
            'perpSide': self.side(perpetrator.player.team),
            'mightyBlow': mighty_blow,
        }
        return new_step

    def define_push(self, data):
        """Define a push dict."""
        new_step = {
            'action': data['action'],
            'stepType': 'push',
            'side': data['targetSide'],
            'num': data['targetNum'],
            'x0': data['x0'],
            'y0': data['y0'],
            'x1': data['x1'],
            'y1': data['y1'],
        }
        return new_step

    def define_follow_up(self, data):
        """Define a followUp dict."""
        new_step = {
            'action': data['action'],
            'stepType': 'followUp',
            'targetNum': data['targetNum'],
            'side': data['side'],
            'num': data['num'],
            'x0': data['x0'],
            'y0': data['y0'],
            'x1': data['x1'],
            'y1': data['y1'],
            'choice': None,
        }
        return new_step



def start_match(home_team, away_team, first_kicking_team=None,
                home_first_direction=None):
    """Create a match between the two sides."""
    if first_kicking_team is None:
        # Replace this with a random selection
        first_kicking_team = 'home'
    if home_first_direction is None:
        # Replace this with a random selection
        home_first_direction = 'right'
    match = Match(
        home_team=home_team,
        away_team=away_team,
        current_side=first_kicking_team,
        first_kicking_team=first_kicking_team,
        home_first_direction=home_first_direction,
        home_rerolls=home_team.rerolls,
        away_rerolls=away_team.rerolls,
        home_rerolls_total=home_team.rerolls,
        away_rerolls_total=away_team.rerolls,
        )
    match.save()
    for home_player in home_team.player_set.all():
        create_pig(home_player, match=match, xpos=0, ypos=0,
                   on_pitch=True, side='home').save()
    for away_player in away_team.player_set.all():
        create_pig(away_player, match=match, xpos=0, ypos=0,
                   on_pitch=True, side='away').save()
    set_kickoff(match, first_kicking_team)
    return match

def set_kickoff(match, kicking_team):
    """Set a kickoff for this match."""
    # Work out which side of the pitch each team is on
    if ((match.home_first_direction == 'right' and match.turn_number <= 8) or
        (match.home_first_direction == 'left' and match.turn_number >= 9)):
        xpos_home = 0
        xpos_away = 25
    else:
        xpos_home = 25
        xpos_away = 0
    # Start placing players at the top of the pitch
    ypos_home = 0
    ypos_away = 0
    for pig in match.playeringame_set.all():
        if pig.player.team == match.home_team:
            pig.xpos = xpos_home
            pig.ypos = ypos_home
            if ypos_home == 14:
                # Reached the bottom of the pitch, wrap back up to the top
                ypos_home = 0
                if xpos_home < 13:
                    xpos_home += 1
                else:
                    xpos_home -= 1
            else:
                ypos_home += 1
        else:
            pig.xpos = xpos_away
            pig.ypos = ypos_away
            if ypos_away == 14:
                # Reached the bottom of the pitch, wrap back up to the top
                ypos_away = 0
                if xpos_away < 13:
                    xpos_away += 1
                else:
                    xpos_away -= 1
            else:
                ypos_away += 1
        pig.down = False
        pig.stunned = False
        pig.stunned_this_turn = False
        pig.tackle_zones = True
        pig.has_ball = False
        pig.move_left = pig.ma
        pig.action = ''
        pig.finished_action = False
        pig.save()
    match.n_to_place = 2
    match.kicking_team = kicking_team
    match.current_side = kicking_team
    match.x_ball = None
    match.y_ball = None
    match.turn_type = 'placePlayers'
    match.save()


class PlayerInGame(models.Model):
    player = models.ForeignKey(Player)
    match = models.ForeignKey(Match)
    side = models.CharField(max_length=4)
    xpos = models.IntegerField()
    ypos = models.IntegerField()
    ma = models.IntegerField()
    st = models.IntegerField()
    ag = models.IntegerField()
    av = models.IntegerField()
    skills = models.TextField()
    effects = models.TextField()
    action = models.CharField(max_length=8)
    move_left = models.IntegerField()
    finished_action = models.BooleanField(default=False)
    down = models.BooleanField(default=False)
    stunned = models.BooleanField(default=False)
    stunned_this_turn = models.BooleanField(default=False)
    has_ball = models.BooleanField(default=False)
    on_pitch = models.BooleanField(default=False)
    knocked_out = models.BooleanField(default=False)
    casualty = models.BooleanField(default=False)
    sent_off = models.BooleanField(default=False)
    tackle_zones = models.BooleanField(default=True)

    def __str__(self):
        return self.player.name

    def as_dict(self):
        result_dict = {
            'side': self.side,
            'name': self.player.name,
            'num': self.player.number,
            'position': self.player.position.title,
            'race': self.player.race,
            'xpos': self.xpos,
            'ypos': self.ypos,
            'ma': self.ma,
            'st': self.st,
            'ag': self.ag,
            'av': self.av,
            'skills': self.skills.split(','),
            'effects': self.effects.split(','),
            'action': self.action,
            'moveLeft': self.move_left,
            'finishedAction': self.finished_action,
            'down': self.down,
            'stunned': self.stunned,
            'stunnedThisTurn': self.stunned_this_turn,
            'hasBall': self.has_ball,
            'onPitch': self.on_pitch,
            'knockedOut': self.knocked_out,
            'casualty': self.casualty,
            'sentOff': self.sent_off,
            'tackleZones': self.tackle_zones,
        }
        return result_dict

    def has_skill(self, skill):
        return skill in self.skills.split(',')
        
    def affected(self, effect):
        return effect in self.effects.split(',')
        
    def add_effect(self, effect):
        if not self.affected(effect):
            if len(self.effects) != 0:
                self.effects = self.effects + ','
            self.effects = self.effects + effect
            self.save()
            
    def remove_effect(self, effect):
        mat = re.match('^(.+,)?(?P<effect>'+effect+')(,.+)?$', self.effects)
        if not mat:
            return
        start = mat.start('effect')
        finish = mat.end('effect')
        if start > 0:
            # Also remove a preceding comma
            start -= 1
        else:
            if finish < len(self.effects):
                # Instead, remove a following comma
                finish += 1
            else:
                # There are no commas!
                pass
        self.effects = self.effects[:start] + self.effects[finish:]
        self.save()

    def set_action(self, action):
        """Set this player's action, and finish the previous player's."""
        self.action = action
        self.save()
        self.match.finish_previous_action(self)

    def n_tackle_zones(self, exclude=None):
        """Return the number of tackle zones on this player."""
        opponents = PlayerInGame.objects.filter(
            match=self.match, 
            xpos__gt=(self.xpos-2), ypos__gt=(self.ypos-2), 
            xpos__lt=(self.xpos+2), ypos__lt=(self.ypos+2), 
            tackle_zones=True, on_pitch=True)
        opponents = opponents.exclude(
            player__team=self.player.team)
        if exclude is not None:
            opponents = opponents.exclude(player__number=exclude.player.number)
        return opponents.count()


def create_pig(parent, **kwargs):
    pig = PlayerInGame()
    pig.player = parent
    pig.ma = parent.ma
    pig.st = parent.st
    pig.ag = parent.ag
    pig.av = parent.av
    pig.skills = parent.skills
    pig.move_left = parent.ma
    for key, value in kwargs.items():
        setattr(pig, key, value)
    return pig


class Step(models.Model):
    step_type = models.CharField(max_length=20)
    action = models.CharField(max_length=20)
    match = models.ForeignKey(Match)
    history_position = models.IntegerField()
    properties = models.TextField()
    result = models.TextField()

    class Meta:
        unique_together = ('match', 'history_position')

    def __str__(self):
        return 'Match {} step {}'.format(self.match.id, self.history_position)

    def properties_dict(self):
        if self.properties:
            return json.loads(self.properties)
        else:
            return {}

    def as_dict(self):
        step_dict = self.properties_dict()
        if self.result:
            result_dict = json.loads(self.result)
        else:
            result_dict = {}
        step_dict['result'] = result_dict
        step_dict['stepType'] = self.step_type
        step_dict['matchId'] = self.match.id
        step_dict['historyPosition'] = self.history_position
        return step_dict

    def player(self):
        """Find out which player is the main focus of this step."""
        properties = self.properties_dict()
        team = self.match.team(properties['side'])
        num = properties['num']
        player = PlayerInGame.objects.get(
            match=self.match, player__team=team, player__number=num)
        return player

    def previous(self):
        """Return the previous step."""
        return Step.objects.get(
            match=self.match, history_position=self.history_position-1)

# def previous_step(match, data):
#     """Return the previous step from the match"""
#     history = Step.objects.filter(match=match).order_by('-history_position')
#     return history[1]





