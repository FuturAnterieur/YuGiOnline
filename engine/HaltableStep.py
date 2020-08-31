from engine.Cards import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE, FACEUPTOOPPONENT

import engine.Action
from engine.TriggerEvent import TriggerEvent

import engine.Effect

class HaltableStep:
    def __init__(self, parentAction):
        self.parentAction = parentAction
        if parentAction is not None:
            self.args = self.parentAction.args

class DoNothing(HaltableStep):
    def run(self, gamestate):
        pass

class AppendToActionStack(HaltableStep):
    def run(self, gamestate):
        gamestate.action_stack.append(self.parentAction)

class PopActionStack(HaltableStep):
    def run(self, gamestate):
        gamestate.action_stack.pop()

class AppendToLRAIfRecording(HaltableStep):
    
    def run(self, gamestate):
        if gamestate.record_LRA:
            gamestate.lastresolvedactions.append(self.parentAction)

class ClearLRAIfRecording(HaltableStep):

    def run(self, gamestate):
        if gamestate.record_LRA:
            gamestate.lastresolvedactions.clear()

class EnableLRARecording(HaltableStep):

    def run(self, gamestate):
        gamestate.record_LRA = True

class DisableLRARecording(HaltableStep):

    def run(self, gamestate):
        gamestate.record_LRA = False

def TranslateTriggerCategory(trigger, gamestate):
    player_str = "TP" if trigger.card.owner == gamestate.turnplayer else "OP"

    return trigger.category + player_str


class ProcessIfTriggers(HaltableStep): #this step should be run at the end of each action
    
    def run(self, gamestate):
        
        triggers_to_run_queue = {'MTP' : [], 'MOP' : []}

        for trigger in gamestate.if_triggers:
            if trigger.matches(self.parentAction, gamestate):
                full_category = TranslateTriggerCategory(trigger, gamestate)
                if trigger.can_be_chained_now(gamestate): 
                    #checks if we are building a chain and if the trigger's spell 
                    #speed is >= to the current spell speed 
                    
                    if full_category == 'MTP' or full_category == 'MOP':
                        triggers_to_run_queue[full_category].append(trigger)
                        #the triggers in this container will be automatically added to a SEGOC chain
                        #at the response window following the next resolution of events
                    else:
                        #if the category is OTP or OOP
                        gamestate.chainable_optional_if_triggers[full_category].append(trigger)
                        #this container will be checked by the reqs function of if-trigger effects.
                        #it is also cleared after each chain response window function
                        #If-effects can only be activated at the first possible opportunity

                else:
                    gamestate.saved_if_triggers[full_category].append(trigger) 
                    #where they are saved for the next SEGOC chain (following the next resolution of events)

        #TODO : player choice of trigger order if there are many triggers in the same category
        for trigger in triggers_to_run_queue['MTP']:
            gamestate.triggers_to_run.append(trigger)
        
        for trigger in triggers_to_run_queue['MOP']:
            gamestate.triggers_to_run.append(trigger)

        


class ProcessFlipTriggers(HaltableStep):
    def run(self, gamestate):
        for trigger in gamestate.flip_triggers:
            if trigger.matches(self.parentAction, gamestate):
                #if we are in the damage step, the flip effect triggers at After Damage Calculation
                if gamestate.curphase == "battle_phase" and gamestate.current_battle_phase_step == "damage_step":
                    trigger.effect.ADC_trigger = TriggerEvent("FlipTriggerADC", trigger.card, trigger.effect, 'if', trigger.category, engine.Effect.MatchOnADC) 
                    #to see how MatchOnADC works, check out the TestFunctionOutsideOfClass.py file
                    trigger.effect.ADC_trigger.funclist.extend([trigger.effect.RemoveADCTriggerFromIfTriggers] + trigger.funclist)
                    gamestate.if_triggers.append(trigger.effect.ADC_trigger)

                else:
                    #else, the flip effect behaves like a 'normal' if-trigger
                    full_category = TranslateTriggerCategory(trigger, gamestate)
                    gamestate.saved_if_triggers[full_category].append(trigger)
                    


def refresh_chainable_when_triggers(gamestate): 
    #This will be run at each chain response window as well as at the start of the SEGOC chain building process
    #the chainable_optional_when_triggers container will be emptied after these processes
    #the categories for when triggers : VTP (visible turn player), ITP (invisible turn player), VOP and IOP (for other player)
    for trigger in gamestate.when_triggers:
        full_category = TranslateTriggerCategory(trigger, gamestate)
        for action in gamestate.lastresolvedactions:
            if trigger.matches(action, gamestate):
                gamestate.chainable_optional_when_triggers[full_category].append(trigger)

        if len(gamestate.chainlinks) > 0:
            if trigger.matches(gamestate.chainlinks[-1], gamestate):
                gamestate.chainable_optional_when_triggers[full_category].append(trigger)
        
        
        
        
def clear_chainable_when_triggers(gamestate):
    for category in gamestate.chainable_optional_when_triggers.keys():
        gamestate.chainable_optional_when_triggers[category].clear()

def clear_chainable_if_triggers(gamestate, if_trigger_cat_to_clear = None):
    if if_trigger_cat_to_clear is not None:
        gamestate.chainable_optional_if_triggers[if_trigger_cat_to_clear].clear()

    else:
        for category in gamestate.chainable_optional_if_triggers.keys():
            gamestate.chainable_optional_if_triggers[category].clear()



class RefreshChainableWhenTriggers(HaltableStep):
    def run(self, gamestate):
        refresh_chainable_when_triggers(gamestate)

class ClearChainableWhenTriggers(HaltableStep):
    def run(self, gamestate):
        clear_chainable_when_triggers(gamestate)

class ClearChainableIfTriggers(HaltableStep):
    def run(self, gamestate):
        clear_chainable_if_triggers(gamestate)

class ClearSavedIfTriggers(HaltableStep):
    def run(self, gamestate):
        for category in gamestate.saved_if_triggers.keys():
            gamestate.saved_if_triggers[category].clear()
        

#On the other hand, Immediate triggers can be ran even while a chain is resolving.
#They are mostly there for OnLeaveField triggers of continuous spell and trap cards,
#or other such consequences of continuous effects.
class RunImmediateTriggers(HaltableStep):

    def run(self, gamestate):
        for trigger in gamestate.immediate_triggers:
            if trigger.matches(self.parentAction, gamestate):
                trigger.execute(gamestate)

class AddTriggerToTTR(HaltableStep):
    def __init__(self, trigger):
        self.trigger = trigger

    def run(self, gamestate):
        gamestate.triggers_to_run.append(self.trigger)


"""
This step launches the trigger at the start of the triggers_to_run queue
Every action that builds a chain first checks if there are triggers left
in this queue and, if there are, they run LaunchTTR instead of asking
the players if they want to chain other actions.
"""
class LaunchTTR(HaltableStep):

    def run(self, gamestate):
        #optional if-triggers only have one chance of being activated
        #and are cancelled by the activation of other triggers
        clear_chainable_if_triggers(gamestate)

        #Optional triggers should also have an execute function for this.
        #It will call their activation action.
        trigger = gamestate.triggers_to_run.pop(0)
        trigger.execute(gamestate)

class InitAndRunAction(HaltableStep):
    def __init__(self, pA, ChildActionClassName, *cargs):
        super(InitAndRunAction, self).__init__(pA)
        self.ChildAction = ChildActionClassName()
        self.ChildActionArgs = cargs

    def run(self, gamestate):
        self.ResolvedChildActionArgs = []
        for carg in self.ChildActionArgs:
            self.ResolvedChildActionArgs.append(self.args[carg])
        self.ChildAction.init(*self.ResolvedChildActionArgs)
        self.ChildAction.run(gamestate)

class RunAction(HaltableStep):
    def __init__(self, pA, ChildActionToRun):
        super(RunAction, self).__init__(pA)
        self.ChildAction = ChildActionToRun

    def run(self, gamestate):
        self.ChildAction.run(gamestate)

class RunStepIfCondition(HaltableStep):
    def __init__(self, pA, step, condition_func, *cf_arg_names):
        super(RunStepIfCondition, self).__init__(pA)
        self.Step = step
        self.condition_func = condition_func
        self.condition_func_arg_names = cf_arg_names

    def run(self, gamestate):
        if (self.condition_func(gamestate, self.args, *self.condition_func_arg_names)):
            self.Step.run(gamestate)

class RunStepIfElseCondition(HaltableStep):
    def __init__(self, pA, stepif, stepelse, condition_func, *cf_arg_names):
        super(RunStepIfElseCondition, self).__init__(pA)
        self.StepIf = stepif
        self.StepElse = stepelse
        self.condition_func = condition_func
        self.condition_func_arg_names = cf_arg_names

    def run(self, gamestate):
        if (self.condition_func(gamestate, self.args, *self.condition_func_arg_names)):
            self.StepIf.run(gamestate)
        else:
            self.StepElse.run(gamestate)

class DestroyCardServer(HaltableStep):
    def __init__(self, pA, destroyedcard_arg_name):
        super(DestroyCardServer, self).__init__(pA)
        self.dan = destroyedcard_arg_name

    def run(self, gamestate):
        
        card = self.args[self.dan]
        player = card.owner
        
        zonenum = card.zone.zonenum
        card.zonearray.pop_card(zonenum)
        
        player.graveyard.add_card(card)


class DrawCardServer(HaltableStep):
    def __init__(self, pA, drawncard_arg_name):
        super(DrawCardServer, self).__init__(pA)
        self.dan = drawncard_arg_name

    def run(self, gamestate):
        drawncard = self.args['player'].deckzone.pop_card()
        self.args['player'].hand.add_card(drawncard)
        drawncard.face_up = FACEUPTOCONTROLLER
        self.args[self.dan] = drawncard

        print("Player " + str(self.args['player'].player_id) + " has drawn " + drawncard.name)


class NSMCServer(HaltableStep): #NormalSummonMonsterCoreServer
    def __init__(self, pA, summonedmonster_arg_name, zone_arg_name, position_arg_name):
        super(NSMCServer, self).__init__(pA)
        self.sman = summonedmonster_arg_name
        self.zan = zone_arg_name
        self.pan = position_arg_name

    def run(self, gamestate):
        summonedmonster = self.args[self.sman]
        
        player = summonedmonster.owner
        player.hand.remove_card(summonedmonster)
        player.monsterzones.add_card(summonedmonster, self.args[self.zan].zonenum)
        summonedmonster.position = self.args[self.pan]
        
class SetSpellTrapServer(HaltableStep):
    def __init__(self, pA, card_arg_name):
        super(SetSpellTrapServer, self).__init__(pA)
        self.can = card_arg_name

    def run(self, gamestate):
        card = self.args[self.can]
        player = card.owner
        player.hand.remove_card(card)
        
        card.face_up = FACEDOWN

        chosenzonenum = 3
        player.spelltrapzones.add_card(card, chosenzonenum)
        card.wassetthisturn = True

class ActivateNormalTrapBeforeActivate(HaltableStep):
    def __init__(self, pA, card_arg_name, effect_arg_name):
        super(ActivateNormalTrapBeforeActivate, self).__init__(pA)
        self.can = card_arg_name
        self.ean = effect_arg_name

    def run(self, gamestate):
        card = self.args[self.can]
        effect = self.args[self.ean]

        gamestate.curspellspeed = effect.spellspeed

        card.face_up = FACEUPTOEVERYONE

class CallEffectActivate(HaltableStep):
    def __init__(self, pA, effect_arg_name):
        super(CallEffectActivate, self).__init__(pA)
        self.ean = effect_arg_name

    def run(self, gamestate):
        self.args[self.ean].Activate(gamestate)

class CallEffectResolve(HaltableStep):
    def __init__(self, pA, effect_arg_name):
        super(CallEffectResolve, self).__init__(pA)
        self.ean = effect_arg_name

    def run(self, gamestate):
        self.args[self.ean].Resolve(gamestate)

class PerformDamageCalculation(HaltableStep):
    def run(self, gamestate):
        target = self.args['target']
        attackingplayer = self.args['player']
        targetplayer = attackingplayer.other
        attackingmonster = self.args['attacking_monster']

        if (target == 'direct_attack'):
            targetplayer.add_life_points(gamestate, -1*attackingmonster.attack)
            
        else:
            targetstat = 0
            
            if target.position == "DEF":
                targetstat = target.defense
                
            else:
                targetstat = target.attack
            
            difference = attackingmonster.attack - targetstat

            winnermonster = attackingmonster if difference > 0 else target
            losermonster = attackingmonster if difference < 0 else target

            if difference == 0 and target.positon == "ATK":
                gamestate.monsters_to_be_destroyed_by_battle.extend([winnermonster, losermonster])

            else:
                if winnermonster.position == "ATK":
                    gamestate.monsters_to_be_destroyed_by_battle.append(losermonster)

                if losermonster.position == "ATK":
                    losermonster.owner.add_life_points(gamestate, -1*math.fabs(difference))



class AppendToChainLinks(HaltableStep):
    def run(self, gamestate):
        gamestate.chainlinks.append(self.parentAction)

class PopChainLinks(HaltableStep):
    def run(self, gamestate):
        gamestate.chainlinks.pop()

class SetBuildingChain(HaltableStep):
    def run(self, gamestate):
        gamestate.is_building_a_chain = True

class UnsetBuildingChain(HaltableStep):
    def run(self, gamestate):
        gamestate.is_building_a_chain = False


class LowerOuterActionStackLevel(HaltableStep):
    def run(self, gamestate):
        gamestate.outer_action_stack_level -= 1
        
class SetSummonNegationWindow(HaltableStep):
    def __init__(self, pA):
        super(SetSummonNegationWindow, self).__init__(pA)

    def run(self, gamestate):
        gamestate.insummonnegationwindow = self.parentAction

class UnsetSummonNegationWindow(HaltableStep):
    def __init__(self, pA):
        super(UnsetSummonNegationWindow, self).__init__(pA)

    def run(self, gamestate):
        gamestate.insummonnegationwindow = None

class CreateCard(HaltableStep):
    def __init__(self, pA, card_arg_name, zone_arg_name):
        super(CreateCard, self).__init__(pA)
        self.can = card_arg_name
        self.zan = zone_arg_name

    def run(self, gamestate):
        self.card = self.args[self.can]
        self.fromzone = self.args[self.zan]
        self.player = self.args['player']

        gamestate.cards_in_play.append(self.card)

        gamestate.sio.emit('create_card', {'cardid' : str(self.card.ID), 'rotation': "Vertical", 'zone':self.fromzone.name, 
                                            'player' : str(self.player.player_id), 'imgpath' : self.card.imgpath}, 
                                            room="duel" + str(gamestate.duel_id) + "_public_info")

        gamestate.sio.emit('change_card_visibility', {'cardid' : str(self.card.ID), 'visibility' : "1"}, 
                    room = "duel" + str(gamestate.duel_id) + "_spectator_info")

class EraseCard(HaltableStep):
    def __init__(self, pA, card_arg_name):
        super(EraseCard, self).__init__(pA)
        self.can = card_arg_name
    
    def run(self, gamestate):
        self.card = self.args[self.can]
        gamestate.cards_in_play.remove(self.card)

        gamestate.sio.emit('erase_card', {'cardid' : str(self.card.ID)}, room="duel" + str(gamestate.duel_id) + "_public_info")

class AddCardToChainSendsToGraveyard(HaltableStep):
    def __init__(self, pA, card_arg_name):
        super(AddCardToChainSendsToGraveyard, self).__init__(pA)
        self.can = card_arg_name

    def run(self, gamestate):
        card = self.args[self.can]
        gamestate.cards_chain_sends_to_graveyard.append({'card' : card, 'was_negated' : self.parentAction.was_negated})

class ChangeCardVisibility(HaltableStep):
    def __init__(self, pA, list_of_player_arg_names, card_arg_name, visibility):
        super(ChangeCardVisibility, self).__init__(pA)
        self.list_of_pan = list_of_player_arg_names
        self.can = card_arg_name
        self.visibility = visibility
   
    def run(self, gamestate):
        card = self.args[self.can]
        for pan in self.list_of_pan:
            player = self.args[pan]
            gamestate.sio.emit('change_card_visibility', {'cardid' : str(card.ID), 'visibility' : self.visibility}, 
                    room = "duel" + str(gamestate.duel_id) + "_player" + str(player.player_id) + "_info")
        
class MoveCard(HaltableStep):
    def __init__(self, pA, card_arg_name, zone_arg_name):
        super(MoveCard, self).__init__(pA)
        self.can = card_arg_name
        self.zan = zone_arg_name

    def run(self, gamestate):
        self.card = self.args[self.can]
        self.tozone = self.args[self.zan]
        
        gamestate.sio.emit('move_card', {'cardid': str(self.card.ID), 'zone': self.tozone.name}, room="duel" + str(gamestate.duel_id) + "_public_info")

        for sid in gamestate.dict_of_sids.values():
            gamestate.waiting_for_players.add(sid)

        gamestate.keep_running_steps = False #the move_completed message from the clients will unhalt the gamestate, 
                                                #by re-calling gamestate.run_steps and setting keep_running_messages to True

class RotateCard(HaltableStep):
    def __init__(self, pA, card_arg_name, rotation_arg_name):
        super(RotateCard, self).__init__(pA)
        self.can = card_arg_name
        self.ran = rotation_arg_name

    def run(self, gamestate):
        card = self.args[self.can]
        rotation = self.args[self.ran]
        gamestate.sio.emit('rotate_card', {'cardid' : str(card.ID), 'rotation' : rotation}, room = "duel" + str(gamestate.duel_id) + "_public_info")

        for sid in gamestate.dict_of_sids.values():
            gamestate.waiting_for_players.add(sid)

        gamestate.keep_running_steps = False


class ChooseOccupiedZone(HaltableStep):
    def __init__(self, pA, zonetype, deciding_player_arg_name, target_player_arg_name, chosen_card_arg_name):
        super(ChooseOccupiedZone, self).__init__(pA)
        self.zonetype = zonetype
        self.dpan = deciding_player_arg_name
        self.tpan = target_player_arg_name
        self.ccan = chosen_card_arg_name

    def run(self, gamestate):
        deciding_player = self.args[self.dpan]
        target_player = self.args[self.tpan]
        
        gamestate.sio.emit('choose_card', {'zonetype' : self.zonetype, 'target_player' : str(target_player.player_id)},
                                        room =  "duel" + str(gamestate.duel_id) + "_player" + str(deciding_player.player_id) + "_info")

        gamestate.action_waiting_for_a_card_choice = self.parentAction
        gamestate.answer_arg_name = self.ccan
        gamestate.keep_running_steps = False

class AskQuestion(HaltableStep):
    def __init__(self, pA, player_arg_name, question, choices, answer_arg_name):
        super(AskQuestion, self).__init__(pA)
        self.pan = player_arg_name
        self.choices = choices
        self.question = question
        self.aan = answer_arg_name

    def run(self, gamestate):
        asked_player = self.args[self.pan]
        choices = self.choices
        question = self.question

        gamestate.sio.emit('ask_question', {'question' : question, 'choices' : choices}, room =  "duel" + str(gamestate.duel_id) + "_player" + str(asked_player.player_id) + "_info")

        gamestate.step_waiting_for_answer = self
        gamestate.answer_arg_name = self.aan
        gamestate.keep_running_steps = False


class OpenWindowForResponse(HaltableStep):  
    #this could be turned into an AskQuestion class with arguments, but would require an extra step for getting the possible_cards
    def __init__(self, pA, response_type, responding_player_arg_name, answer_arg_name):
        super(OpenWindowForResponse, self).__init__(pA)
        self.rpan = responding_player_arg_name
        self.aan = answer_arg_name
        self.response_type = response_type

    def run(self, gamestate):

        responding_player = self.args[self.rpan]
        waiting_player = responding_player.other
        #check if responding player can play something first
        
        refresh_chainable_when_triggers(gamestate)

        possible_cards, choices_per_card = gamestate.get_available_choices(responding_player)
        
        answer_choices = 'Yes_No' if len(possible_cards) > 0 else 'No'
        
        gamestate.sio.emit('start_waiting', {'reason' : self.response_type},
                                room =  "duel" + str(gamestate.duel_id) + "_player" + str(waiting_player.player_id) + "_info")
        gamestate.sio.emit('ask_question', {'question' : self.response_type, 'choices' : answer_choices}, 
                                room =  "duel" + str(gamestate.duel_id) + "_player" + str(responding_player.player_id) + "_info")
        #the client will send back the question so that the server knows what to do according to the answer.
        #if it is No, then sio.emit will give control back to the waiting player and resume executing steps

        #if it is Yes, then sio.emit will set the responding player in a 'regular' choose-a-card-and-action mode.
        #once he has selected his action, the waiting player will be unfrozen, gamestate.run_action_asked_for will be called on the action
        #and steps will thus resume their execution.

        gamestate.step_waiting_for_answer = self
        gamestate.answer_arg_name = self.aan
        gamestate.keep_running_steps = False
        
class SetMultipleActionWindow(HaltableStep):
    def __init__(self, controlling_player, current_phase_or_step):
        super(SetMultipleActionWindow, self).__init__(None)
        self.controlling_player = controlling_player
        self.current_phase_or_step = current_phase_or_step
    
    def run(self, gamestate):
        #Note that refresh_chainable_when_triggers is not run here 
        #(and a refresh is always followed by a clearing of the chainable triggers container once the window closes),
        #so when-triggers can only be ran in a response window,
        #and not from an open game state (represented by the SetMutltipleActionWindow step).


        gamestate.player_in_multiple_action_window = self.controlling_player

        waiting_player = self.controlling_player.other

        gamestate.sio.emit('start_waiting', {'reason' : self.current_phase_or_step},
                                room =  "duel" + str(gamestate.duel_id) + "_player" + str(waiting_player.player_id) + "_info")
        gamestate.sio.emit('multiple_action_window', {'current_phase_or_step' : self.current_phase_or_step}, 
                                room =  "duel" + str(gamestate.duel_id) + "_player" + str(self.controlling_player.player_id) + "_info")

        gamestate.keep_running_steps = False
        gamestate.player_to_stop_waiting_when_run_action = waiting_player

class LetTurnPlayerChooseNextPhase(HaltableStep):
    def __init__(self):
        super(LetTurnPlayerChooseNextPhase, self).__init__(None)

    def run(self, gamestate):
        gamestate.sio.emit('choose_next_phase', {}, room =  "duel" + str(gamestate.duel_id) + "_player" + str(gamestate.turnplayer.player_id) + "_info")
        gamestate.sio.emit('start_waiting', {'reason' : 'phase_changing'}, 
                    room =  "duel" + str(gamestate.duel_id) + "_player" + str(gamestate.otherplayer.player_id) + "_info")

        gamestate.keep_running_steps = False


class CancelAttackInGamestate(HaltableStep):
    def run(self, gamestate):
        gamestate.attack_declared = False
        gamestate.attack_declared_action = None

class RunDrawPhase(HaltableStep):
    def __init__(self):
        super(RunDrawPhase, self).__init__(None)

    def run(self, gamestate):
        gamestate.draw_phase()

class RunStandbyPhase(HaltableStep):
    def __init__(self):
        super(RunStandbyPhase, self).__init__(None)

    def run(self, gamestate):
        gamestate.standby_phase()

class SetMainPhase1(HaltableStep):
    def __init__(self):
        super(SetMainPhase1, self).__init__(None)

    def run(self, gamestate):
        gamestate.set_main_phase_1()

class SetBattleStep(HaltableStep):
    def __init__(self):
        super(SetBattleStep, self).__init__(None)

    def run(self, gamestate):
        gamestate.current_battle_phase_step = 'battle_step'
        gamestate.attack_declared = False
        gamestate.attack_declared_action = None
        gamestate.immediate_triggers.append(gamestate.AttackReplayTrigger)


        

