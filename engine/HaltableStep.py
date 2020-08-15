from engine.Cards import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE, FACEUPTOOPPONENT

import engine.Action

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

class ProcessIfTriggers(HaltableStep): #this step should be run at the end of each action
    
    def run(self, gamestate):
        
        triggers_to_run_queue = {'MTP' : [], 'MOP' : []}

        for trigger in gamestate.if_triggers:
            if trigger.matches(self.parentAction):
                if trigger.can_be_chained_now(gamestate): #checks if we are in a chain and the trigger's spell speed is >= to the current spell speed 
                    if trigger.category == 'MTP' or trigger.category == 'MOP':
                        triggers_to_run_queue[trigger.category].append(trigger)
                    else:
                        gamestate.chainable_optional_if_triggers[trigger.category].append(trigger)
                        #this container is cleared after each chain response window function
                        #If-effects can only be activated at the first possible opportunity

                else:
                    gamestate.saved_if_triggers[trigger.category].append(trigger) #where they are saved for the next SEGOC chain

        #TODO : player choice of trigger order if there are many triggers in the same category
        for trigger in triggers_to_run_queue['MTP']:
            gamestate.triggers_to_run.append(trigger)
        
        for trigger in triggers_to_run_queue['MOP']:
            gamestate.triggers_to_run.append(trigger)

        
        #{'MTP_triggers_to_run' : [], 'MOP_triggers_to_run' : [], etc}
        #here the categories are 'MTP_TTR', 'MOP_TTR', 'OTP_TTR', 'OOP_TTR'
        #as well as 'OWTP_TTR' and 'OWOP_TTR' for when-effects that can miss their timing
        
#Outside of a SEGOC situation, or in a chain that was previously built through SEGOC,
#no responding action is specified at the start, so the response window opens normally and optional if-triggers
#can be activated during it.
#But activating an optional if-trigger in a response window should remove it from the TTR container.
#So the response window could check if any optional if and when-triggers have been registered and present them 
#as choices to the responding player, in addition to the possible choices of Ignition effects (that don't work through triggers).

#Some mandatory effects are Quick, and in the case where they are activated, they automatically go on the current chain.
#if many mandatory quick effects activate at the same time, they go on the chain in SEGOC order,
#and some limitations apply to how their effects are resolved (e.g. if they are both negating effects,
#only the first one may accomplish its original goal; the second one goes on the chain but cannot do anything. See
#https://www.yomifrog.lima-city.de/xgm/en/Extended_Game_Mechanics_-_Chapter_6.php#p1)

"""
Quick Effects in SEGOC
It is also possible that Quick Effects are chained simultaneuosly. This mostly happens when Quick Effects try to negate something and they are mandatory at the same time. An optional Quick Effect can never be activated simultaneuosly. Mandatory effects ALWAYS take precedence over optional effects.

Example:

Player A controls "Horus, the Black Flame Dragon LV8" and "Light and Darkness Dragon". Player B activates a Spell Card.

    "Light and Darkness Dragon" automatically chains as chain link 2.
    "Horus" cannot be activated in this case because he has an optional Quick Effect.


If there are 2 monsters with a negating mandatory Quick Effect, we use SEGOC. The outcome is quite interesting.

Example:

Player A's "Sangan" is sent from the field to the graveyard. Player A also controls a face-up "Light and Darkness Dragon". Player B controls a "Doomcaliber Knight".

    Because we have 2 mandatory effects, both effects HAVE TO chain to "Sangan's" effect.
    First, the "Light and Darkness Dragon" from the Turn Player is added to the chain.
    Chain link 3 is the non-Turn Player's "Doomcaliber Knight", which also activated in response to "Sangan".
    Resolve: In the resolve, "Doomcaliber Knight" resolves without effect, because negating effects need to be chained directly to the effect they want to negate.
    Afterwards, "Light and Darkness Dragon" negates "Sangan" after loosing 500 ATK/DEF.


Negating effects can only negate those effects that they are directly chained to. "Doomcaliber Knight" is not directly chained to "Sangan", but he is chained to "Light and Darkness Dragon's" effect. "Doomcaliber Knight" cannot simply negate "Light and Darkness Dragon" because he triggered when "Sangan" activated.
"""
#this makes me think that for each trigger, I should keep the action(s) that triggered it in memory.


#mandatory triggers will be ran through their execute function,
#while optional triggers will be ran through their corresponding action; 
#not the one they are matching as an activation condition, but the one 
#that actually does the Activate and Resolve steps. For example,
#Seven Tools of the Bandit has a When a trap card is Activated activation condition (implemented through its reqs and trigger.matches),
#and its action is an instance of ActivateNormalTrap. Its Effect.Activate is to Pay 1000 LP as an activation cost and its 
#Effect.Resolve is to negate the activation (and if you do destroy it). 
#The Effect's reqs will include a 'corresponding trigger in the TTR_container' clause.

#So optional triggers should not need to have an execute function.

#But what happens if an optional if-trigger is registered, but cannot be activated (or is not selected by its player) 
#during the current chain/sequence of events?
#-if it is because its spell speed is too low and/or the chain is already resolving, we can defer it to a new chain through SEGOC
#-is it possible for a 'response to an activation'-type effect to use an if-trigger? In that case, a situation where e.g. 
#the activation requirement is met at chain link 2 but not at chain link 4, while the if-trigger should still activate, would be possible.

"""
So the algorithm for building a chain could go like this.
First, we check if another effect is in the simultaneous batch (used by SEGOC and simulateneous mandatory quick-effects; called gamestate.triggers_to_run_in_order) and add it to the chain (and remove it from the batch) if there is one.

(
If mandatory quick effects are triggered while the current spell speed is at 2 and spell speed 1 effects are registered, the spell speed 1 effects will still
be registered while the mandatory quick effects will go in the simultaneous batch.
So that 'placing of mandatory spell speed 2 effects in the simultaneous batch' has to be done in RegisterTriggers.

The spell speed 1 effects will be processed by RunSEGOCTriggers after the current chain resolved, and be transferred to the simultaneous batch after this processing.

I once thought that I could remove the simultaneous batch and just run a condition of 'Mandatory triggers first', but I think that
the simultaneous batch is still necessary for cases of multiple spell speed 1 effects triggering at the same time for a SEGOC; if no priority is given to themthrough the simultaneous batch, they will be ignored because of the standard spell speed rule (outside of a SEGOC situation, you can only chain spell speed 2 or higher effects).
)

Next, since all mandatory effects are covered by the simultaneous batch (as explained above), we check for optional effects.
Registered spell speed 1 if-effects are saved for the next chain (to be built through SEGOC), while when-effects get periodically canceled.
When-effects that did not miss their timing are given as choices;
But now the dilemma is that 'do I explicitly ask the player if he wants to activate each effect, or do I just present him his open board?'
This dilemma is especially troublesome in the case of spell speed 2 optional if-effects (that may miss their timing).

REMEMBER
- that when-effects can still respond to the event at the base of the chain (before chain link 1)
- that when-effects can never respond to an event that is part of an activation cost.

So I would need a list of 'events that can currently be responded to'.

BUT ALSO

- when-effects can be grouped together with if-effects in SEGOC chains

"""

def refresh_chainable_when_triggers(gamestate): #This will be run at each chain response window as well as at the start of the SEGOC chain building process
    for trigger in gamestate.when_triggers:
        for action in gamestate.lastresolvedactions:
            if trigger.matches[action]:
                gamestate.chainable_optional_when_triggers[trigger.category].append(trigger)

        if trigger.matches(gamestate.chainlinks[-1]):
            gamestate.chainable_optional_when_triggers[trigger.category].append(trigger)
        
        #the categories for when triggers : VTP (visible turn player), ITP (invisible turn player), VOP and IOP (for other player)
        #the container will be emptied after these processes
        
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
        clear_chainale_when_triggers(gamestate)

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
            if trigger.matches(self.parentAction):
                trigger.execute(gamestate)

class LaunchTTR(HaltableStep):

    def run(self, gamestate):
        #optional if-triggers only have one chance of being activated
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
        
        #to do : separate Action subclass for "send to graveyard"
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
    def __init__(self, pA, summonedmonster_arg_name, zone_arg_name):
        super(NSMCServer, self).__init__(pA)
        self.sman = summonedmonster_arg_name
        self.zan = zone_arg_name

    def run(self, gamestate):
        summonedmonster = self.args[self.sman]
        gamestate.normalsummonscounter += 1
        player = summonedmonster.owner
        player.hand.remove_card(summonedmonster)
        player.monsterzones.add_card(summonedmonster, self.args[self.zan].zonenum)

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

        gamestate.sio.emit('create_card', {'cardid' : str(self.card.ID), 'zone':self.fromzone.name, 'player' : str(self.player.player_id)}, 
                                            room="duel" + str(gamestate.duel_id) + "_public_info")

class EraseCard(HaltableStep):
    def __init__(self, pA, card_arg_name):
        super(CreateCard, self).__init__(pA)
        self.can = card_arg_name
    
    def run(self, gamestate):
        self.card = self.args[self.can]
        gamestate.sio.emit('erase_card', {'cardid' : str(self.card.ID)}, room="duel" + str(gamestate.duel_id) + "_public_info")

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
        
        if_trigger_cat_to_clear = 'OTP' if responding_player == gamestate.turnplayer else 'OOP'

        clear_chainable_if_triggers(gamestate, if_trigger_cat_to_clear)
        clear_chainable_when_triggers(gamestate)

        answer_choices = 'Yes_No' if len(possible_cards) > 0 else 'No'
        
        gamestate.sio.emit('start_waiting', {'reason' : self.response_type}, room =  "duel" + str(gamestate.duel_id) + "_player" + str(waiting_player.player_id) + "_info")
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




        

