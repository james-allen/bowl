from game.models import PlayerInGame

import random

def find_player(match, data):
    """Find out which player it is."""
    if data['side'] == 'home':
        team = match.home_team
    elif data['side'] == 'away':
        team = match.away_team
    num = data['num']
    player = PlayerInGame.objects.get(
        match=match, player__team=team, player__number=num)
    return player

def resolve(match, step_type, data):
    if step_type == 'reroll':
        if data['rerollType'] == 'team':
            if data['side'] == 'home':
                match.home_rerolls -= 1
                match.home_reroll_used_this_turn = True
            else:
                match.away_rerolls -= 1
                match.away_reroll_used_this_turn = True
            match.save()
        step_type = data['rerollStepType']
    if step_type in ['move', 'push', 'followUp']:
        # A move step
        if step_type == 'followUp' and data['choice'] == 'false':
            return {}
        player = find_player(match, data)
        # Update the player's position in the database
        player.xpos = data['x1']
        player.ypos = data['y1']
        player.save()
        if player.has_ball:
            # Move the ball too
            match.x_ball = data['x1']
            match.y_ball = data['y1']
            match.save()
        if step_type == 'push' and data['offPitch'] == 'true':
            player.on_pitch = False
            injury_roll = roll_injury_dice()
            if injury_roll['result'] == 'knockedOut':
                player.knocked_out = True
            elif injury_roll['result'] == 'casualty':
                player.casualty = True
            player.save()
            result = {'injuryRoll': injury_roll}
        else:
            result = {}
        return result
    elif step_type == 'block':
        # A block step
        # Find out which is the attacking player
        if data['side'] == 'home':
            attacking_team = match.home_team
            defending_team = match.away_team
        elif data['side'] == 'away':
            attacking_team = match.away_team
            defending_team = match.home_team
        attacking_num = int(data['num'])
        defending_num = int(data['targetNum'])
        attacking_player = PlayerInGame.objects.get(
            match=match, player__team=attacking_team, 
            player__number=attacking_num)
        defending_player = PlayerInGame.objects.get(
            match=match, player__team=defending_team,
            player__number=defending_num)
        attack_st = attacking_player.player.st
        for player in PlayerInGame.objects.filter(
            match=match, player__team=attacking_team,
            xpos__gt=(defending_player.xpos-2),
            xpos__lt=(defending_player.xpos+2),
            ypos__gt=(defending_player.ypos-2),
            ypos__lt=(defending_player.ypos+2),
            on_pitch=True, down=False):
            if player != attacking_player and n_tackle_zones(player) == 1:
                attack_st += 1
        defence_st = defending_player.player.st
        for player in PlayerInGame.objects.filter(
            match=match, player__team=defending_team,
            xpos__gt=(attacking_player.xpos-2),
            xpos__lt=(attacking_player.xpos+2),
            ypos__gt=(attacking_player.ypos-2),
            ypos__lt=(attacking_player.ypos+2),
            on_pitch=True, down=False):
            if player != defending_player and n_tackle_zones(player) == 1:
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
        result = roll_block_dice(n_dice)
        result['attackSt'] = attack_st
        result['defenceSt'] = defence_st
        return result
    elif step_type == 'foul':
        # A foul on a player
        # Find out which is the attacking player
        if data['side'] == 'home':
            attacking_team = match.home_team
            defending_team = match.away_team
        elif data['side'] == 'away':
            attacking_team = match.away_team
            defending_team = match.home_team
        attacking_num = int(data['num'])
        defending_num = int(data['targetNum'])
        attacking_player = PlayerInGame.objects.get(
            match=match, player__team=attacking_team, 
            player__number=attacking_num)
        defending_player = PlayerInGame.objects.get(
            match=match, player__team=defending_team,
            player__number=defending_num)
        modifier = 0
        for player in PlayerInGame.objects.filter(
            match=match, player__team=attacking_team,
            xpos__gt=(defending_player.xpos-2),
            xpos__lt=(defending_player.xpos+2),
            ypos__gt=(defending_player.ypos-2),
            ypos__lt=(defending_player.ypos+2),
            on_pitch=True, down=False):
            if player != attacking_player and n_tackle_zones(player) == 0:
                modifier += 1
        for player in PlayerInGame.objects.filter(
            match=match, player__team=defending_team,
            xpos__gt=(attacking_player.xpos-2),
            xpos__lt=(attacking_player.xpos+2),
            ypos__gt=(attacking_player.ypos-2),
            ypos__lt=(attacking_player.ypos+2),
            on_pitch=True, down=False):
            if player != defending_player and n_tackle_zones(player) == 1:
                modifier -= 1
        # Roll against armour
        armour_roll = roll_armour_dice(defending_player, modifier)
        if armour_roll['success']:
            injury_roll = roll_injury_dice()
            if injury_roll['result'] == 'stunned':
                defending_player.stunned = True
            elif injury_roll['result'] == 'knockedOut':
                defending_player.knocked_out = True
                defending_player.on_pitch = False
            elif injury_roll['result'] == 'casualty':
                defending_player.casualty = True
                defending_player.on_pitch = False
            else:
                raise ValueError('Injury roll returned unexpected result: ' + 
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
            attacking_player.save()
        return {'armourRoll': armour_roll, 'injuryRoll': injury_roll, 
                'sentOff': sent_off}
    elif step_type == 'knockDown':
        # A player knocked over
        player = find_player(match, data)
        # Knock the player over in the database
        player.down = True
        player.has_ball = False
        player.save()
        # Roll against armour
        armour_roll = roll_armour_dice(player)
        if armour_roll['success']:
            injury_roll = roll_injury_dice()
            if injury_roll['result'] == 'stunned':
                player.stunned = True
            elif injury_roll['result'] == 'knockedOut':
                player.knocked_out = True
                player.on_pitch = False
            elif injury_roll['result'] == 'casualty':
                player.casualty = True
                player.on_pitch = False
            else:
                raise ValueError('Injury roll returned unexpected result: ' + 
                                 injury_roll['result'])
            player.save()
        else:
            injury_roll = None
        return {'armourRoll': armour_roll, 'injuryRoll': injury_roll}
    elif step_type == 'standUp':
        # A player standing up
        player = find_player(match, data)
        if player.player.ma < 3:
            dice = roll_dice(6, 1)
            success = dice['dice'][0] >= 4
        else:
            dice = None
            success = True
        if success:
            player.down = False
            player.save()
        return {'dice': dice, 'success': success}
    elif step_type == 'pickUp':
        # A player picking up the ball
        player = find_player(match, data)
        modifier = 1 - n_tackle_zones(player)
        result = roll_agility_dice(player, modifier=modifier)
        if result['success']:
            player.has_ball = True
            player.save()
        return result
    elif step_type == 'scatter':
        # Scattering the ball
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
        match.x_ball = x_ball
        match.y_ball = y_ball
        match.save()
        return {'dice': dice, 'direction': direction, 
                'x1': x_ball, 'y1': y_ball,
                'lastX': last_x, 'lastY': last_y}
    elif step_type == 'catch':
        # Catching the ball
        player = find_player(match, data)
        if player.down:
            return {'success': False}
        modifier = - n_tackle_zones(player)
        if data['accurate']:
            modifier += 1
        result = roll_agility_dice(player, modifier=modifier)
        if result['success']:
            player.has_ball = True
            player.save()
        return result
    elif step_type == 'pass':
        # Pass the ball
        player = find_player(match, data)
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
        modifier -= n_tackle_zones(player)
        result = roll_agility_dice(player, modifier=modifier)
        fumble = (min(result['rawResult'], result['modifiedResult']) <= 1)
        if fumble:
            result['success'] = False
        else:
            match.x_ball = int(data['x1'])
            match.y_ball = int(data['y1'])
            match.save()
            result['x1'] = match.x_ball
            result['y1'] = match.y_ball
        result['fumble'] = fumble
        player.has_ball = False
        player.save()
        return result
    elif step_type == 'handOff':
        # Hand-Off the ball to an adjacent player
        # Always successful
        match.x_ball = int(data['x1'])
        match.y_ball = int(data['y1'])
        match.save()
        return {}
    elif step_type == 'throwin':
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
        compass = direction + 2 * edge
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
        while not on_pitch(x1, y1):
            x1 = last_x
            y1 = last_y
            last_x = x1 - x_dir
            last_y = y1 - y_dir
        return {'x1': x1, 'y1': y1, 'lastX': last_x, 'lastY': last_y}
    elif step_type == 'endTurn':
        match.home_reroll_used_this_turn = False;
        match.away_reroll_used_this_turn = False;
        match.save()
        return {}

def n_tackle_zones(player):
    opponents = PlayerInGame.objects.filter(
        match=player.match)
    opponents = opponents.exclude(
        player__team=player.player.team)
    opponents = opponents.filter(
        xpos__gt=(player.xpos-2), ypos__gt=(player.ypos-2))
    opponents = opponents.filter(
        xpos__lt=(player.xpos+2), ypos__lt=(player.ypos+2))
    opponents = opponents.filter(
        down=False)
    return opponents.count()

def roll_block_dice(n_dice):
    result_num = roll_dice(6, n_dice)
    block_dice_dict = {
        1: "attackerDown",
        2: "bothDown",
        3: "pushed",
        4: "pushed",
        5: "defenderStumbles",
        6: "defenderDown"
    }
    return {"nDice": n_dice,
        "dice": [block_dice_dict[num] for num in result_num["dice"]]}

def roll_armour_dice(player, modifier=0):
    dice = roll_dice(6, 2)
    raw_result = sum(dice['dice'])
    modified_result = raw_result + modifier
    success = (modified_result > player.player.av)
    return {'dice': dice, 'rawResult': raw_result, 
            'modifiedResult': modified_result, 'success': success}

def roll_injury_dice(modifier=0):
    dice = roll_dice(6, 2)
    raw_result = sum(dice['dice'])
    modified_result = raw_result + modifier
    if modified_result <= 7:
        result = 'stunned'
    elif modified_result <= 9:
        result = 'knockedOut'
    else:
        result = 'casualty'
    return {'dice': dice, 'rawResult': raw_result, 
            'modifiedResult': modified_result, 'result': result}

def roll_agility_dice(player, modifier=0):
    dice = roll_dice(6, 1)
    raw_result = sum(dice['dice'])
    modified_result = raw_result + modifier
    if raw_result == 1:
        success = False
    elif raw_result == 6:
        success = True
    else:
        success = ((modified_result + min(player.player.ag, 6)) >= 7)
    return {'dice': dice, 'rawResult': raw_result, 
            'modifiedResult': modified_result, 'success': success}

def roll_dice(n_sides, n_dice):
    return {"nDice": n_dice,
        "dice": [random.randint(1, n_sides) for i in range(n_dice)]}

def is_double(dice):
    return dice['dice'][0] == dice['dice'][1]

def find_pass_range(delta_x, delta_y):
    if ((delta_x <= 1 and delta_y <= 3) or
        (delta_x == 2 and delta_y <= 2) or
        (delta_x == 3 and delta_y <= 1)):
        return 'quickPass'
    elif ((delta_x <= 3 and delta_y <= 6) or
          (delta_x == 4 and delta_y <= 5) or
          (delta_x == 5 and delta_y <= 4) or
          (delta_x == 6 and delta_y <= 3)):
        return 'shortPass'
    elif ((delta_x <= 2 and delta_y <= 10) or
          (delta_x <= 4 and delta_y <= 9) or
          (delta_x <= 6 and delta_y <= 8) or
          (delta_x == 7 and delta_y <= 7) or
          (delta_x == 8 and delta_y <= 6) or
          (delta_x == 9 and delta_y <= 4) or
          (delta_x == 10 and delta_y <= 2)):
        return 'longPass'
    elif ((delta_x <= 1 and delta_y <= 13) or
          (delta_x <= 4 and delta_y <= 12) or
          (delta_x <= 6 and delta_y <= 11) or
          (delta_x <= 8 and delta_y <= 10) or
          (delta_x == 9 and delta_y <= 9) or
          (delta_x == 10 and delta_y <= 8) or
          (delta_x == 11 and delta_y <= 6) or
          (delta_x == 12 and delta_y <= 4) or
          (delta_x == 13 and delta_y <= 1)):
        return 'longBomb'
    else:
        return 'outOfRange'

def on_pitch(xpos, ypos):
    return 0 <= xpos < 26 and 0 <= ypos < 15


