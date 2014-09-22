"""Various utility functions."""

import random

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

def roll_injury_dice(player, modifier=0):
    dice = roll_dice(6, 2)
    raw_result = sum(dice['dice'])
    modified_result = raw_result + modifier
    thick_skull = player.has_skill('Thick Skull')
    regeneration = player.has_skill('Regeneration')
    if modified_result <= 7 or (modified_result == 8 and thick_skull):
        result = 'stunned'
    elif modified_result <= 9:
        result = 'knockedOut'
    else:
        result = 'casualty'
        if regeneration:
            regeneration_dice = roll_dice(6, 1)
            regeneration_success = regeneration_dice['dice'][0] >= 4
            if regeneration_success:
                # Actually, they've regenerated!
                result = 'regenerated'
    result_dict = {'dice': dice, 'rawResult': raw_result, 
                   'modifiedResult': modified_result, 'result': result}
    if regeneration:
        result_dict['regeneration'] = {'dice': regeneration_dice,
                                       'success': regeneration_success}
    return result_dict

def roll_agility_dice(player, modifier=0):
    required_result = 7 - min(player.player.ag, 6)
    dice = roll_dice(6, 1)
    raw_result = sum(dice['dice'])
    modified_result = raw_result + modifier
    if raw_result == 1:
        success = False
    elif raw_result == 6:
        success = True
    else:
        success = (modified_result >= required_result)
    return {'dice': dice, 'rawResult': raw_result, 
            'modifiedResult': modified_result, 
            'requiredResult': required_result, 'success': success}

def roll_dice(n_sides, n_dice):
    return {"nDice": n_dice,
        "dice": [random.randint(1, n_sides) for _ in range(n_dice)]}

def is_double(dice):
    return dice['dice'][0] == dice['dice'][1]

def on_pitch(xpos, ypos):
    return 0 <= xpos < 26 and 0 <= ypos < 15

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

def other_side(side):
    if side == 'home':
        return 'away'
    elif side == 'away':
        return 'home'
    else:
        raise ValueError('Unrecognised side: ' + side)

def add_next_step(result, next_step):
    """Add a nextStep to the result dictionary."""
    if 'nextStep' not in result:
        result['nextStep'] = []
    result['nextStep'].append(next_step)
    return        
