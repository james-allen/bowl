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
        return {}
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
        n_dice = 1
        if attacking_player.player.st > (2 * defending_player.player.st):
            n_dice = 3
        elif attacking_player.player.st > defending_player.player.st:
            n_dice = 2
        elif (2 * attacking_player.player.st) < defending_player.player.st:
            n_dice = 3
        elif attacking_player.player.st < defending_player.player.st:
            n_dice = 2
        return roll_block_dice(n_dice)
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
        dice = roll_dice(8, 1)
        direction = sum(dice['dice'])
        if direction in [1, 4, 6]:
            x1 = int(data['x0']) - 1
        elif direction in [3, 5, 8]:
            x1 = int(data['x0']) + 1
        else:
            x1 = int(data['x0'])
        if direction in [1, 2, 3]:
            y1 = int(data['y0']) - 1
        elif direction in [6, 7, 8]:
            y1 = int(data['y0']) + 1
        else:
            y1 = int(data['y0'])
        match.x_ball = x1
        match.y_ball = y1
        match.save()
        return {'dice': dice, 'direction': direction, 'x1': x1, 'y1': y1}
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
    elif step_type == 'endTurn':
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

def roll_armour_dice(player):
    dice = roll_dice(6, 2)
    total = sum(dice['dice'])
    success = (total > player.player.av)
    return {'dice': dice, 'total': total, 'success': success}

def roll_injury_dice():
    dice = roll_dice(6, 2)
    total = sum(dice['dice'])
    if total <= 7:
        result = 'stunned'
    elif total <= 9:
        result = 'knockedOut'
    else:
        result = 'casualty'
    return {'dice': dice, 'total': total, 'result': result}

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
        