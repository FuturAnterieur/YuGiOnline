import engine.HaltableStep
from engine.defs import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE, FACEUPTOOPPONENT, CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, STATE_NOTINEFFECT, STATE_EVENT, STATE_ACTIVATE, STATE_RESOLVE, CAUSE_BATTLE, CAUSE_CHAIN, CAUSE_TRIBUTE


class Action:
    def init(self, name, card, parent_effect = None):
        self.name = name
        self.card = card
        self.parent_effect = parent_effect
        if card is not None:
            self.player = card.owner
        self.was_negated = False
        
    def check_for_bans(self, gamestate, effect_state = STATE_NOTINEFFECT):
        unbanned = True
        for ban in gamestate.bans:
            if ban.bans_action(self, gamestate, effect_state):
                unbanned = False
                break

        return unbanned

    def check_for_immunities(self, card, effect_state = STATE_NOTINEFFECT):
        compatible = True
        for effect in card.effects:
            if effect.blocks_action(self, effect_state):
                compatible = False
                break

        return compatible

    def check_for_bans_and_immunities(self, card, gamestate, effect_state = STATE_NOTINEFFECT):
        return self.check_for_bans(gamestate, effect_state) and self.check_for_immunities(card, effect_state) 

    def run(self, gamestate):  #I'll have to do the same for reqs
        self.__class__.run_func(self, gamestate)

    def run_steps(self, gamestate, on_run_list_of_steps = None):
        lot_to_run = self.list_of_steps if on_run_list_of_steps == None else on_run_list_of_steps

        for i in range(len(lot_to_run) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(lot_to_run[i])

        gamestate.run_steps()

class RunOptionalResponseWindows(Action):
    def init(self, firstplayer, event_type):
        self.args = {}
        self.args['firstplayer'] = firstplayer
        self.args['secondplayer'] = firstplayer.other
        self.event_type = event_type

    def run(self, gamestate):
        #chainable_optional_fast_respond_events are cleared after each of these steps automatically.
        
        step2 = engine.HaltableStep.OpenWindowForResponse(self, 'response_window:' + self.event_type, 'firstplayer', 'FirstplayerUsesRW')
        step3 = engine.HaltableStep.RunStepIfCondition(self, 
                engine.HaltableStep.OpenWindowForResponse(self, 'response_window:' + self.event_type, 'secondplayer', 'SecondplayerUsesRW'), 
                RunOtherPlayerWindowCondition, 'FirstplayerUsesRW')
        
        list_of_steps = [step2, step3]

        self.run_steps(gamestate, list_of_steps)


class RunResponseWindows(Action):
    #Running ProcessMandatoryResponseEvents (which adds to TriggersToRun if there are) and then going to LaunchTTR or RunOptionalResponseWindows 

    def init(self, firstplayer, event_type):
        self.event_type = event_type
        self.args = {}
        self.args['firstplayer'] = firstplayer
        self.args['event_type'] = event_type

    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.ProcessMandatoryRespondEvents(self), 
                                TTREmpty),
                         engine.HaltableStep.RunStepIfElseCondition(self, 
                            engine.HaltableStep.LaunchTTR(self),
                            engine.HaltableStep.InitAndRunAction(self, RunOptionalResponseWindows, 'firstplayer', 'event_type'), 
                            TTRNonEmpty)]

        self.run_steps(gamestate, list_of_steps)

def TTRNonEmpty(gamestate, args):
    return len(gamestate.triggers_to_run) > 0

def TTREmpty(gamestate, args):
    return len(gamestate.triggers_to_run) == 0

def RunOtherPlayerWindowCondition(gamestate, args, answer_arg_name):
    answer = args[answer_arg_name]
    return answer == "No"


"""
The idea with RunEventsCondition is that a further sequence of events (maybe including a chain) can always
be launched from the RunEvents of the pre-existing one. Every time a RunEvents at the end of a sequence of events happens, 
the outer action stack level is raised by 1.
"""
def RunEventsCondition(gamestate, args):
    return len(gamestate.action_stack) == gamestate.outer_action_stack_level + 1

def EndOfChainCondition(gamestate, args):
    return len(gamestate.chainlinks) == 0

def RunMAWForOtherPlayerCondition(gamestate, args):
    return gamestate.player_in_multiple_action_window == gamestate.otherplayer

def RunIfSaysYes(gamestate, args, answer_arg_name):
    answer = args[answer_arg_name]
    return answer == "Yes"


class RunEvents(Action): #this function will always be ran at the end of a chain or sequence of events
    def __init__(self, for_what_event, at_end_of_events = True):
        self.at_end_of_events = at_end_of_events
        self.for_what_event = for_what_event

    def ask_trigger_steps_util(self, trigger, player_arg_name):
        return [engine.HaltableStep.AskQuestion(self, player_arg_name, 'want_to_activate_trigger:' + trigger.effect.name, ['Yes', 'No'], 'want_to_activate_trigger_answer' ),
            engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.AddTriggerToTTR(trigger), RunIfSaysYes, 'want_to_activate_trigger_answer') ]

    def run(self, gamestate):
        self.args = {}
        self.args['turnplayer'] = gamestate.turnplayer
        self.args['otherplayer'] = gamestate.otherplayer
        self.args['for_what_event'] = self.for_what_event

        if (self.at_end_of_events):
            gamestate.outer_action_stack_level += 1


        engine.HaltableStep.refresh_SEGOC_events(gamestate)

        
        engine.HaltableStep.refresh_chainable_optional_fast_trigger_events(gamestate) 
        #these won't be put on the SEGOC chain, but they can be chained afterwards
        #(either on top of the SEGOC effects or by starting a chain of their own if no SEGOC chain is formed)

        list_of_steps = []

        
        for trigger in gamestate.chainable_events['trigger_MSS1TP'] + gamestate.chainable_events['respond_MSS1TP']:
            #if there is more than one trigger in a category and we are building a SEGOC chain, 
            #which we will always be doing since we are at the end of a previous chain, ask the player 
            #who owns the effects how he wants to order them in the chain
            gamestate.triggers_to_run.append(trigger)

        for trigger in gamestate.chainable_events['trigger_MSS1OP'] + gamestate.chainable_events['respond_MSS1OP']: #meme principe pour les autres
            gamestate.triggers_to_run.append(trigger)

        for trigger in gamestate.chainable_events['trigger_OSS1TP'] + gamestate.chainable_events['respond_OSS1TP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'turnplayer'))

        for trigger in gamestate.chainable_events['trigger_OSS1OP'] + gamestate.chainable_events['respond_OSS1OP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'otherplayer'))


        
        #what happens when an optional effect is triggered and scheduled for a SEGOC chain?
        #the choice is given to the player to activate the effect or not,
        #and then, if there is more than one trigger in the category,
        #the player who owns them decides in which order they get stacked on the chain
        #(same principle as for mandatory effects).
        
        #then run the chain
        
        #at the end I do something almost equivalent to RunResponseWindows, but without engine.HaltableStep.ProcessMandatoryRespondEvents(self),
        #since those will only have an effect if there is already something in the gamestate.chainlinks stack and there is nothing
        #in the SEGOC triggers_to_run container.

        #well, according to how those MandatoryRespondEvents seem to work up to now, at least.
        #I don't know if they can be activated in response to LastResolvedActions too.

        list_of_steps.extend([engine.HaltableStep.ClearSEGOCChainableEvents(self),
                                engine.HaltableStep.ClearSavedTriggerEvents(self),  #we don't need those anymore
                                engine.HaltableStep.RunStepIfElseCondition(self, 
                                        engine.HaltableStep.LaunchTTR(self),
                                        engine.HaltableStep.InitAndRunAction(self, RunOptionalResponseWindows, 'turnplayer', 'for_what_event'),
                                        TTRNonEmpty),
                                engine.HaltableStep.ClearChainableOptionalFastTriggerEvents(self)]) 
                                #these were built at the start of the current call to RunEvents
                                #the Clear as an ending step is to clear them at the exit of all the 
                                #calls to RunEvents that might have happened.
        
        if (self.at_end_of_events):
            list_of_steps.append(engine.HaltableStep.LowerOuterActionStackLevel(self))
        
        #the same structure of If-Else LaunchTTR vs RunResponseWindows can be used inside the Actions that constitute chain links

        #this will call the run of the first action in the triggers_to_run list

        #doing a run_steps should suffice after that.    

        #Actions that add to chains should have an option to specify another action that takes the place of their response window
        #so that pre-built SEGOC chains can be made

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()
       
def ActionStackEmpty(gamestate, args):
    return len(gamestate.action_stack) == 0

class RunMAWsAtEnd(Action):

    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, gamestate.curphase)]

        if gamestate.player_in_multiple_action_window == gamestate.otherplayer:
            list_of_steps.append(engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, gamestate.curphase))
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()

class DrawCard(Action):
    
    def init(self, player, in_draw_phase = True):
        super(DrawCard, self).init("Draw Card", None)
        self.player = player
        self.args = {'player' : player, 'fromzone' : player.deckzone, 'tozone' : player.hand}
        self.in_draw_phase = in_draw_phase

    def reqs(self, gamestate): #unused in the current version
        if len(self.player.deckzone.cards) > 0:
            return True
        else:
            return False

    def default_run(self, gamestate):
        run_triggers_step = engine.HaltableStep.RunStepIfCondition(self, 
                        engine.HaltableStep.RunAction(self, RunEvents('Card drawn')), 
                        RunEventsCondition) if self.in_draw_phase == False else engine.HaltableStep.DoNothing(self)

        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.DrawCardServer(self, 'drawncard'),
                        engine.HaltableStep.StopDuelIfVictoryCondition(self),
                        engine.HaltableStep.CreateCard(self, 'drawncard', 'fromzone'),
                        engine.HaltableStep.ChangeCardVisibility(self, ['player'], 'drawncard', '1'),
                        engine.HaltableStep.MoveCard(self, 'drawncard', 'tozone'),
                        engine.HaltableStep.ProcessTriggerEvents(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self),
                        engine.HaltableStep.RunImmediateEvents(self),
                        run_triggers_step,
                        engine.HaltableStep.PopActionStack(self)]
    
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
    
        gamestate.run_steps()

    run_func = default_run

#reqs-less actions are there mostly just for triggers
def steps_for_event_action(action, gamestate):
    list_of_steps = [engine.HaltableStep.RunImmediateEvents(action),
                    engine.HaltableStep.ProcessTriggerEvents(action),
                    engine.HaltableStep.AppendToLRAIfRecording(action)]

    return list_of_steps

def steps_for_event_pre_action(action, gamestate):
    list_of_steps = [engine.HaltableStep.RunImmediateEvents(action)]
    
    return list_of_steps

class PreCardLeavesZoneEvents(Action):
    def init(self, card, zone, parentAction):
        super().init("PreCardLeaves" + zone.type, card)
        self.zone = zone
        self.parentAction = parentAction
        self.args = self.parentAction.args

    def run(self, gamestate):
        los = steps_for_event_pre_action(self, gamestate)
        self.run_steps(gamestate, los)

class PreCardSentToZoneEvents(Action):
    def init(self, card, zone, parentAction):
        super().init("PreCardSentTo" + zone.type, card)
        self.zone = zone
        self.parentAction = parentAction
        self.args = self.parentAction.args

    def run(self, gamestate):
        los = steps_for_event_pre_action(self, gamestate)
        self.run_steps(gamestate, los)

class ApplyBansForChangeCardZone(Action):
    def init(self, card, parentAction):
        super().init("Bans application for CCZ", card)
        self.parentAction = parentAction
        self.args = self.parentAction.args

    def run(self, gamestate):
        los = steps_for_event_pre_action(self, gamestate)
        self.run_steps(gamestate, los)

class CardLeavesZoneEvents(Action):
    def init(self, card, zone):
        super().init("Card Leaves " + zone.type, card)
        self.zone = zone
        self.args = {}

    def default_run(self, gamestate):
        #but its run_trigger_events has to be properly ordered in respect to other actions
        
        #gamestate.clear_lra_if_at_no_triggers() 
        #this is only a sequential sub-action (an intermediate step) so its LRA should be stacked with
        #already existing ones

        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)

    run_func = default_run

class CardSentToZoneEvents(Action):
    def init(self, card, zone):
        super().init("Card sent to " + zone.type, card)
        self.args = {}
        self.zone = zone

    def default_run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)

    run_func = default_run
        
class  TurnOffPassiveEffects(Action):
    def init(self, card, zone):
        super().init('Utility effect deactivation for leaving ' + zone.type, card)
        self.args = {}
        self.zone = zone

    def default_run(self, gamestate):
        los = steps_for_event_pre_action(self, gamestate)
        self.run_steps(gamestate, los)

    run_func = default_run



#attempt to merge Destroy, Banish, Discard and Return To Hand in a single, at-run-time modifiable action

def EraseIfGYOrBanished(gamestate, args, tozone_arg_name):
    tozone = args[tozone_arg_name]
    return tozone.type == "Graveyard" or tozone.type == "Banished"


class ChangeCardZone(Action):
    
    def init(self, name, card, cause, parent_effect = None, is_contained = False, with_leave_zone_trigger = True):
        super().init(name, card, parent_effect)
        
        tozone = ""
        if name == CCZBANISH:
            tozone = card.owner.banished
        elif name == CCZRETURNTOHAND:
            tozone = card.owner.hand
        else:
            tozone = card.owner.graveyard

        self.intended_action = name
        self.intended_tozone = tozone    
        self.args = {'card' : card, 'fromzone' : card.zone, 'tozone' : tozone, 'this_action' : self}
        self.is_contained = is_contained
        self.with_leave_zone_trigger = with_leave_zone_trigger
        self.parent_effect = parent_effect
        
    def default_run(self, gamestate):
        
        clear_lra_step = engine.HaltableStep.DoNothing(self) if self.is_contained else engine.HaltableStep.ClearLRAIfRecording(self)
        lzt_step = engine.HaltableStep.InitAndRunAction(self, CardLeavesZoneEvents, 'card', 'fromzone') if self.with_leave_zone_trigger else engine.HaltableStep.DoNothing(self)
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                            clear_lra_step,
                            engine.HaltableStep.InitAndRunAction(self, PreCardLeavesZoneEvents, 'card', 'fromzone', 'this_action'), 
                            #This is for 'banish it when it leaves the field'-type triggers
                            engine.HaltableStep.InitAndRunAction(self, PreCardSentToZoneEvents, 'card', 'tozone', 'this_action'), 
                            engine.HaltableStep.InitAndRunAction(self, TurnOffPassiveEffects, 'card', 'fromzone'),
                             engine.HaltableStep.InitAndRunAction(self, ApplyBansForChangeCardZone, 'card', 'this_action'),
                            #for deactivating cards when they leave the field, mostly
                            engine.HaltableStep.MoveCard(self, 'card', 'tozone'),
                            engine.HaltableStep.RunStepIfCondition(self, 
                                    engine.HaltableStep.EraseCard(self, 'card'),
                                    EraseIfGYOrBanished, 'tozone'),
                            engine.HaltableStep.ChangeCardZoneServer(self, 'card', 'tozone'),
                            lzt_step,
                            engine.HaltableStep.InitAndRunAction(self, CardSentToZoneEvents, 'card', 'tozone'),
                            engine.HaltableStep.ProcessTriggerEvents(self),
                            engine.HaltableStep.AppendToLRAIfRecording(self),
                            engine.HaltableStep.RunImmediateEvents(self),
                            engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.RunAction(self, RunEvents(self.name)), RunEventsCondition),
                            engine.HaltableStep.PopActionStack(self),
                            engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        

        gamestate.run_steps()


    run_func = default_run

class ChainSendsToGraveyard(Action):
    def run(self, gamestate):
        self.args = {'this_action' : self}
        
        gamestate.curspellspeed = 0

        list_of_steps = []
        cardcounter = 0

        self.args = {'action' : CCZDESTROY, 'is_contained' : True, 'cause' : CAUSE_CHAIN, 'effect' : None}

        for cardinfo in gamestate.cards_chain_sends_to_graveyard:
            card = cardinfo['card']
            if card.location != 'Graveyard' and card.location != 'Banished':
                self.args['card' + str(cardcounter)] = card
                self.args['wlft' + str(cardcounter)] = not cardinfo['was_negated']
                #this check might be redundant but I'm keeping just in case a card gets sent to the graveyard
                #AFTER its call to AddCardToChainSendsToGraveyard
                
                list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, ChangeCardZone, 'action', 
                                                                'card' + str(cardcounter), 'cause', 'effect', 'is_contained', 'wlft' + str(cardcounter)))

                #does the sending of cards to the graveyard at the end of chain activate triggers?
                #the wiki says these events are considered to be simultaneous to the last event in the chain.

                #the wiki also says that if an activation was negated, its corresponding card will be sent to the graveyard if necessary
                #at the end of the chain (as expected) but it will not count as having be sent there from the field.

            cardcounter += 1

        gamestate.cards_chain_sends_to_graveyard.clear()

        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()

class FlipMonsterFaceUp(Action):
    def init(self, card):
        super().init(card)
        self.args = {'monster' : card, 'player1' : card.owner, 'player2' : card.owner.other}

    def run(self, gamestate):
        #no ClearLRA because this will always be a sub-action
        list_of_steps = [engine.HaltableStep.ChangeCardVisibility(self, ['player1', 'player2'], 'monster', "1"),
                        engine.HaltableStep.ProcessFlipEvents(self)]

        #flip effects in a summon situation :
        #they will be added to the saved if-triggers 
        #and will thus be triggered during the SEGOC chain building at the end of the summon.

        #in a battle situation,
        #the RunImmediateEvents will add an if-trigger that triggers at AfterDamageCalculation

        #so a flip trigger's category is 'if' (either mandatory or optional), but it goes in the gamestate.flip_triggers container.
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

class Target(Action):
    def init(self, card, list_of_possible_targets, parent_effect = None):
        super().init('Target', card)
        self.args = {'player' : self.card.owner, 'possible_targets' : list_of_possible_targets, 'chosen_target' : None}
        self.parent_effect = parent_effect
    
    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.ChooseOccupiedZone(self, 'player', 'possible_targets', 'chosen_target')]
        list_of_steps.extend(steps_for_event_action(self))
        self.run_steps(gamestate, list_of_steps)


class SummonMonster(Action):

    def init(self, name, card):
        super(SummonMonster, self).init(name, card)
        

class TributeMonsters(Action):
    
    def init(self, card):
        super(TributeMonsters, self).init("Tribute Monsters", None)
        self.card = card
        self.player = card.owner
        self.args = {'deciding_player' : self.player, 'destroy_is_contained' : True, 'ccz_name' : CCZDESTROY, 
                        'destroy_cause' : CAUSE_TRIBUTE, 'parent_effect' : None, 'this_action' : self}
        
    def reqs(self, gamestate):
        self.player = self.card.owner
        if self.check_for_bans(gamestate) == False:
            return False

        if(len(self.player.monsterzones.occupiedzonenums) < self.card.numtributesrequired):
            return False
        else:
            self.args['possible_tributes'] = self.player.monsters_on_field

            return True
    
    def default_run(self, gamestate):
                 
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self), engine.HaltableStep.ClearLRAIfRecording(self)]
        
        #'Monster' is not an arg from the args dict but a parameter indicating to choose among monster zones
        
        list_of_steps_for_one_tribute = [engine.HaltableStep.ChooseOccupiedZone(self,'deciding_player', 'possible_tributes', 'chosen_monster'),
                                         engine.HaltableStep.InitAndRunAction(self, ChangeCardZone, 'ccz_name', 
                                                    'chosen_monster', 'destroy_cause', 'parent_effect', 'destroy_is_contained')]

        for i in range(self.card.numtributesrequired):
            list_of_steps.extend(list_of_steps_for_one_tribute)

        ending_steps = [engine.HaltableStep.ProcessTriggerEvents(self), engine.HaltableStep.AppendToLRAIfRecording(self), 
                        engine.HaltableStep.RunImmediateEvents(self), 
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunEvents('Monsters tributed')), RunEventsCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]
        
        list_of_steps.extend(ending_steps)
        
        self.run_steps(gamestate, list_of_steps)
        

    run_func = default_run


def CheckIfNotNegated(gamestate, args, action_arg_name):
    action = args[action_arg_name]
    return not action.was_negated


class NormalSummonMonster(SummonMonster):
    
    def init(self, card):
        super().init("Normal Summon Monster", card)
        self.TributeAction = TributeMonsters()
        self.TributeAction.init(self.card)
        self.args = { 'this_action' : self, 'summonedmonster' : card, 'actionplayer' : card.owner, 
                'otherplayer' : card.owner.other, 'event1' : 'Monster would be summoned'}

    def reqs(self, gamestate):
        player = self.card.owner

        if self.check_for_bans(gamestate) == False:
            return False
        
        if player != gamestate.turnplayer or (gamestate.curphase != 'main_phase_1' and gamestate.curphase != 'main_phase_2'):
            return False
        
        if self.card.location != "Hand":
            return False

        if gamestate.normalsummonscounter == 1:
            #print("You have already normal summoned a monster this turn.")
            return False

        if len(gamestate.action_stack) > 0: #equivalent to checking if the game state is open
            return False

        if self.card.numtributesrequired == 0:
            #check if a zone is left
            if len(player.monsterzones.occupiedzonenums) == 5:
                #print("Cannot summon a monster without tributes if no zones are left.")
                return False
            else:
                return True
        else:
            return self.TributeAction.reqs(gamestate)
            

    def default_run(self, gamestate):
        
        def RunTributeCondition(gamestate, args, card_arg_name):
            card = args[card_arg_name]
            return card.numtributesrequired > 0

        gamestate.normalsummonscounter += 1 #optional : put that in a dedicated step (that must go before the summon negation window)
        player = self.card.owner
        self.args['zone_choices'] = [zone for zone in player.monsterzones.listofzones if zone.zonenum not in player.monsterzones.occupiedzonenums]

        #TODO : steps (and javascript) for the selection of a free zone
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, self.TributeAction), 
                                                                                    RunTributeCondition, 'summonedmonster'),
                        engine.HaltableStep.ChooseFreeZone(self, 'actionplayer', 'zone_choices', 'chosen_zone'),
                        engine.HaltableStep.AskQuestion(self, 'actionplayer', 'choose_position', ['ATK', 'DEF'], 'ATK_or_DEF_answer'),  
                        engine.HaltableStep.InitAndRunAction(self, MonsterWouldBeSummonedEvents, 'summonedmonster'),
                        engine.HaltableStep.InitAndRunAction(self, RunOptionalResponseWindows, 'actionplayer', 'event1'), 
                        engine.HaltableStep.RunStepIfCondition(self, 
                            engine.HaltableStep.InitAndRunAction(self, NormalSummonMonsterCore, 'summonedmonster', 'ATK_or_DEF_answer', 'chosen_zone', 'this_action'), 
                            CheckIfNotNegated, 'this_action'),
                        engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.RunAction(self, RunEvents('Tribute and monster summoned')), 
                                RunEventsCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)] 
        #even if the summon is negated, we run RunEvents, because there may be if-triggers that can be run, and even if there isn't any, some when triggers may be activatable (i.e. for the destroy that may have happened during the tribute).

        #the summon negation window must first be open to the action player, and then to the other player if the action player has chosen not to play anything for it.
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        
        gamestate.run_steps()

    run_func = default_run

class MonsterWouldBeSummonedEvents(Action):
    def init(self, card):
        super().init("Monster would be summoned", card)
        self.args = {}

    def run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)

class NormalSummonMonsterCore(Action):
    def init(self, card, position, zone, parentNormalSummonAction):
        super().init("Normal Summon Monster", card)
        self.args = {'summonedmonster': card, 'position' : position, 'chosen_zone' : zone, 
                'action_player' : card.owner, 'other_player' : card.owner.other}
        self.parentNormalSummonAction = parentNormalSummonAction

    def run(self, gamestate):
         #optional when-effects for the destroy occuring in Tribute miss their timing
        list_of_steps = [ engine.HaltableStep.ClearLRAIfRecording(self),
                engine.HaltableStep.NSMCServer(self, 'summonedmonster', 'chosen_zone', 'position'), 
                         engine.HaltableStep.MoveCard(self, 'summonedmonster', 'chosen_zone')]

        if (self.args['position'] == "ATK"):
            list_of_steps.append(engine.HaltableStep.ChangeCardVisibility(self, ['other_player'], 'summonedmonster', "1"))

        elif (self.args['position'] == "DEF"):
            self.args['rotation'] = "Horizontal"
            list_of_steps.extend([engine.HaltableStep.ChangeCardVisibility(self, ['action_player'], 'summonedmonster', "0"),
                                    engine.HaltableStep.RotateCard(self, 'summonedmonster', 'rotation')])

            
        list_of_steps.extend([engine.HaltableStep.ProcessTriggerEvents(self.parentNormalSummonAction),
                              engine.HaltableStep.AppendToLRAIfRecording(self.parentNormalSummonAction),
                              engine.HaltableStep.RunImmediateEvents(self.parentNormalSummonAction)])

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()



class DeclareAttack(Action):

    def init(self, card):
        super(DeclareAttack, self).init("Declare Attack", card)
        self.args = {'odaa' : self, 'player' : self.card.owner, 'target_player' : self.card.owner.other, 
                        'attacking_monster' : card, 'target_arg_name' : 'target'}

        #odaa stands for original declare attack action
    def evaluate_potential_target_monsters(self, gamestate):
       
        list_of_possible_target_monsters = []
        for monster in self.args['target_player'].monsters_on_field:
            compatible = True
            dummy_attack = DeclareAttack(self.card)
            dummy_attack['target'] = monster

            unbanned = dummy_attack.check_for_bans(gamestate)
            if unbanned == False:
                compatible = False

            else:
                not_blocked = dummy_attack.check_for_immunities(monster)
                if not_blocked == False:
                    compatible = False

            if compatible:
                list_of_possible_target_monsters.append(monster)

        return list_of_possible_target_monsters

    def evaluate_if_target_can_still_be_attacked(self, gamestate):
        unbanned = self.check_for_bans(gamestate)
        
        if self.args['target'] == 'direct_attack':
            return unbanned
        else:
            if unbanned == False:
                return False

            compatible = self.check_for_immunities(self.args['target'])
            
            return compatible
    
    def is_direct_attack_possible(self, gamestate):
        sample_direct_attack = DeclareAttack()
        sample_direct_attack.init(self.card)
        sample_direct_attack.args['target'] = 'direct_attack'

        return (self.card.can_attack_directly or len(self.args['target_player'].monsters_on_field) == 0) and sample_direct_attack.check_for_bans(gamestate)

    def reqs(self, gamestate):
        if len(gamestate.action_stack) > 0:
            return False
        
        if gamestate.curphase != "battle_phase":
            return False

        if gamestate.current_battle_phase_step != "battle_step":
            return False
        
        if gamestate.attack_declared == True:
            return False

        if self.card.attacks_declared_this_turn >= self.card.max_attacks_per_turn:
            return False

        if self.check_for_bans(gamestate) == False:
            return False
        
        self.args['possible_targets'] = self.evaluate_potential_target_monsters(gamestate)
        
        is_direct_attack_possible = self.is_direct_attack_possible(gamestate)

        if not is_direct_attack_possible and len(self.args['possible_targets']) == 0:
            return False

        self.card_could_attack_directly = is_direct_attack_possible
        
        return True

    def default_run(self, gamestate):
        self.card.attacks_declared_this_turn += 1
        gamestate.attack_declared = True
        gamestate.attack_declared_action = self
        gamestate.replay_was_triggered = False

        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.InitAndRunAction(self, SelectAttackTarget, 'attacking_monster', 'odaa', 'target_arg_name'),
                        engine.HaltableStep.InitAndRunAction(self, AttackDeclarationEvents, 'odaa'),
                        engine.HaltableStep.InitAndRunAction(self, AttackTargetingEvents, 'odaa'),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunEvents('Attack declared')), 
                            RunEventsCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step')]
        
        self.run_steps(gamestate, list_of_steps)

    run_func = default_run

def DirectAttackChoice(gamestate, args, da_arg_name):
    answer = args[da_arg_name]
    return answer == "Yes"

class SelectAttackTarget(Action):
    def init(self, card, parent_declare_attack_action, target_arg_name):
        super().init("Select attack target", card)
        self.pdaa = parent_declare_attack_action #could replace that with gamestate.attack_declared_action
        self.taa = target_arg_name
        self.args = {}

    def run(self, gamestate):
        list_of_steps = []
        if len(self.pdaa.args['possible_targets']) == 0:
            self.pdaa.args[self.taa] = 'direct_attack'

        else:
            if self.card.can_attack_directly:
                list_of_steps.extend([engine.HaltableStep.AskQuestion(self.pdaa, 'player', "want_attack_directly", ['Yes', 'No'], 'direct_attack_answer'),
                                    engine.HaltableStep.RunStepIfElseCondition(self.pdaa, 
                                        engine.HaltableStep.SetArgToValue(self.pdaa, self.taa, 'direct_attack'),
                                        engine.HaltableStep.ChooseOccupiedZone(self.pdaa, 'player', 'possible_targets', self.taa),
                                        DirectAttackChoice, 'direct_attack_answer')])

            else:
                list_of_steps.extend([engine.HaltableStep.ChooseOccupiedZone(self.pdaa, 'Monster', 'player', 'target_player', self.taa)])

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()


class AttackDeclarationEvents(Action):
    def init(self, parent_declare_attack_action):
        super(AttackDeclarationEvents, self).init("Attack declared", parent_declare_attack_action.card)
        self.pdaa = parent_declare_attack_action
        self.args = self.pdaa.args

    def run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)


class AttackTargetingEvents(Action):
    def init(self, parent_declare_attack_action):
        super(AttackTargetingEvents, self).init("Attack targeting", parent_declare_attack_action.card)
        self.pdaa = parent_declare_attack_action
        self.args = self.pdaa.args

    def run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)

def AttackTargetingReplayCondition(gamestate, args):
    ret = False
    
    is_direct_attack_possible_now = gamestate.attack_declared_action.is_direct_attack_possible(gamestate)

    if gamestate.replay_was_triggered:
        ret = True

    elif gamestate.attack_declared_action.card_could_attack_directly == False and is_direct_attack_possible_now == True:
        ret = True

    elif gamestate.attack_declared_action.evaluate_if_target_can_still_be_attacked(gamestate) == False:
        ret = True
          
    return ret


def RACWasNotCancel(gamestate, args, answer_arg_name):
    return args[answer_arg_name] != "CancelAttack"


class AttackTargetingReplay(Action):
    def init(self, original_declare_attack_action):
        super(AttackTargetingReplay, self).init("Attack replay", parent_declare_attack_action.card)
        self.odaa = original_declare_attack_action
        self.args = self.odaa.args
        self.args['ra'] = self

        #ra stands for replay action
    def default_run(self, gamestate):
        gamestate.replay_was_triggered = False

        is_attack_still_possible = True
        self.odaa.args['possible_targets'] = self.odaa.evaluate_potential_target_monsters()
        is_direct_attack_possible_now = self.odaa.is_direct_attack_possible()
        
        if not is_direct_attack_possible_now and len(self.odaa.args['possible_targets']) == 0:
            is_attack_still_possible = False

        self.odaa.card_could_attack_directly = is_direct_attack_possible_now

        choices = ['CancelAttack', 'SelectTarget'] if is_attack_still_possible else ['CancelAttack']

        gamestate.immediate_events.append(gamestate.AttackReplayTrigger)
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.AskQuestion(self, 'player', "replay_action_choice", choices, 'rac_answer'),
                        engine.HaltableStep.RunStepsIfElseCondition(self, 
                            engine.HaltableStep.InitAndRunAction(self, ReselectTargetCore, 'ra'),
                            engine.HaltableStep.CancelAttackInGamestate(self),
                            RACWasNotCancel, 'rac_answer'),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'battle_phase_battle_step'),
                        engine.HaltableStep.RunAction(self, BattleStepBranchOut())]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

    run_func = default_run

class ReselectTargetCore(Action):
    def init(self, parent_replay_action):
        super().init("Attack replay", parent_declare_attack_action.card)
        self.pra = parent_replay_action
        self.args = self.pra.args
        
    def run(self, gamestate):
        #a replay triggers for 'A monster is targeted by an attack' but not for 'a monster declares an attack'

        
        list_of_steps = [engine.HaltableStep.InitAndRunAction(self, SelectAttackTarget, 'attacking_monster', 'odaa', 'target_arg_name'),
                        engine.HaltableStep.InitAndRunAction(self, AttackTargetingEvents, 'odaa'),
                        engine.HaltableStep.RunStepIfCondition(self, 
                            engine.HaltableStep.RunAction(self, RunEvents('Attack declared (replay)')), 
                            RunEventsCondition)]

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()
    
"""
the battle step ends with BattleStepBranchOut
a replay also ends with this action

In it, we evaluate if a replay is needed through AttackTargetingReplayCondition 
(which just asks for the state of the gamestate.replay_was_triggered variable)

Setting this replay_was_triggered flag belongs to the gamestate.

For now, there is only a trigger checking if an opponent's monster has left the field, 
but we would also need to check for :

- Any situation where The number of monsters on the turn player's opponent's side of the field changes, no matter how briefly
    (so that also means to check if monsters are added to the opponent's side of the field, and to check if there are controllership switches)
This first condition can be dealt with with immediate triggers. But according to the wiki, two other conditions can cause a replay :

- A monster is no longer able to attack.
- A monster that is attacking another monster gains the ability to attack directly due to a card effect.

These two conditions need the change to be permanent to actually cause the replay to happen, and cannot be dealt with with immediate triggers.

"""
class BattleStepBranchOut(Action):
    def run(self, gamestate):
        self.args = {}
        list_of_steps = []

        gamestate.immediate_events.remove(gamestate.AttackReplayTrigger)

        if gamestate.attack_declared == True:
            self.args['ad_action'] = gamestate.attack_declared_action
            
            list_of_steps.append(engine.HaltableStep.RunStepIfElseCondition(self, 
                            engine.HaltableStep.InitAndRunAction(self, AttackTargetingReplay, 'ad_action'),
                            engine.HaltableStep.InitAndRunAction(self, LaunchDamageStep, 'ad_action'), 
                            AttackTargetingReplayCondition))

        else:
            list_of_steps.append(engine.HaltableStep.RunAction(self, LaunchEndStep()))

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

def TargetIsMonsterAndIsFaceDown(gamestate, args, target_arg_name):
    target = args[target_arg_name]
    res = False
    if target != 'direct_attack':
        if target.face_up == FACEDOWN:
            res = True

    return res

def BattlingMonstersStillOnField(gamestate, args, attacker_arg_name, target_arg_name):
    target = args[target_arg_name]
    attacker = args[attacker_arg_name]
    target_on_field = False
    if target == 'direct_attack':
        target_on_field = True
    elif target.location == "Field":
        target_on_field = True

    attacker_on_field = False
    if attacker.location == "Field":
        attacker_on_field = True

    return target_on_field and attacker_on_field


class LaunchDamageStep(Action):
    def init(self, attack_declare_action):
        self.ad_action = attack_declare_action
        self.args = self.ad_action.args
        self.args['ad_action'] = self.ad_action
        self.args['this_action'] = self

    def run(self, gamestate):
        gamestate.current_battle_phase_step = 'damage_step'
        gamestate.indamagestep = True
        list_of_steps = [engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.InitAndRunAction(self, StartOfDamageStepEvents, 'this_action'), 
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_start', False)), 
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_start'),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_start'),
                        engine.HaltableStep.InitAndRunAction(self, BeforeDamageCalculationEvents, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_BDC', False)), 
                        engine.HaltableStep.RunStepIfCondition(self,
                            engine.HaltableStep.InitAndRunAction(self, FlipMonsterFaceUp, 'target'), 
                            TargetIsMonsterAndIsFaceDown, 'target'),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_BDC'),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_BDC'),
                        engine.HaltableStep.RunStepIfCondition(self,
                            engine.HaltableStep.InitAndRunAction(self, RestOfDamageStep, 'this_action'),
                                BattlingMonstersStillOnField, 'attacking_monster', 'target')]
                        

            #a flip effect will work as a mandatory or optional if-effect that triggers at AfterDamageCalculationEvents.
            #Otherwise it could be triggered during the open window following BeforeDamageCalculation.
            #So FlipMonsterFaceUp can be fed immediate triggers that register the monster's flip effect
            #as having to be added to chainable_optional_respond_events at AfterDamageCalculation.
            #It's either that or I implement a special gamestate container for flip-effect monsters 
            #having to trigger their flip-effect at the next AfterDamageCalculation.

            #D.D. Warrior Lady would be a Visible When-Trigger triggering after damage calculation.
            #And remember : Ryko the Lighstworn Hunter (a flip monster) and D.D. Warrior Lady go into a SEGOC chain
            #if they trigger during the same battle.


        list_of_steps.extend([engine.HaltableStep.SetBattleStep(),
                            engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step'),
                            engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'battle_phase_battle_step'),
                            engine.HaltableStep.RunAction(None, engine.Action.BattleStepBranchOut())])

        self.run_steps(gamestate, list_of_steps)
                            

class RestOfDamageStep(Action):
    def init(self, damage_step_action):
        self.ds_action = damage_step_action
        self.ad_action = damage_step_action.ad_action
        self.args = self.ad_action.args
        self.args['ad_action'] = self.ad_action
        self.args['this_action'] = self.ds_action
    
    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.InitAndRunAction(self, DuringDamageCalculation, 'this_action'),
                        engine.HaltableStep.InitAndRunAction(self, AfterDamageCalculationEvents, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_ADC', False)), 
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_ADC'),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_ADC'),
                        engine.HaltableStep.InitAndRunAction(self, BattleSendsMonstersToGraveyard, 'this_action'),
                        engine.HaltableStep.InitAndRunAction(self, EndOfDamageStepEvents, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_end', False)),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_end'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_end'),
                        engine.HaltableStep.InitAndRunAction(self, CeaseDuringDamageStepEffects, 'this_action')]

        self.run_steps(gamestate, list_of_steps)

class DamageStepEventAction(Action):
    def init(self, ds_action):
        self.name = self.__class__.__name__
        self.ds_action = ds_action
        self.args = self.ds_action.args

    def run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)
        
class StartOfDamageStepEvents(DamageStepEventAction):
    def init(self, ds_action):
        super(StartOfDamageStepEvents, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "start"
        super(StartOfDamageStepEvents,self).run(gamestate)

class BeforeDamageCalculationEvents(DamageStepEventAction):
    def init(self, ds_action):
        super(BeforeDamageCalculationEvents, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "before_damage_calculation"
        super(BeforeDamageCalculationEvents,self).run(gamestate)

class DuringDamageCalculation(Action):
    def init(self, ds_action):
        self.ds_action = ds_action
        self.args = ds_action.args

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "during_damage_calculation"
        list_of_steps = [engine.HaltableStep.RunImmediateEvents(self),
                        engine.HaltableStep.ProcessTriggerEvents(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self),
                        engine.HaltableStep.RunAction(self, RunEvents('during damage calculation', False)),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.PerformDamageCalculation(self, 'loserplayer', 'LPamount'),
                        engine.HaltableStep.ChangeLifePointsAnimation(self, 'loserplayer', 'LPamount'),
                        engine.HaltableStep.StopDuelIfVictoryCondition(self),
                        engine.HaltableStep.InitAndRunAction(self, MonstersMarkedEventsForAll, 'this_action')]
                        #engine.HaltableStep.RunAction(self, RunEvents('monsters marked triggers', False))
               
        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

        #this will substract life points and place monsters in the monsters_to_be_destroyed_by_battle container
        #it will also run a MonsterMarkedToBeDestroyedByBattle trigger
        #which probably won't be used as most 'destroyed by battle' effects trigger during the end of the damage step,
        #when the monsters are actually sent to the graveyard.

class MonstersMarkedEventsForAll(Action):
    def init(self, ds_action):
        self.ds_action = ds_action
        self.args = ds_action.args

    def run(self, gamestate):
        list_of_steps = []
        counter = 0
        for monster in gamestate.monsters_to_be_destroyed_by_battle:
            self.args['monster' + str(counter)] = monster
            list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, MonsterMarkedEvents, 'monster' + str(counter)))
        
        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

class MonsterMarkedEvents(Action):
    def init(self, card):
        super(MonsterMarkedEvents, self).init(card)

    def run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)

class AfterDamageCalculationEvents(DamageStepEventAction):
    def init(self, ds_action):
        super(AfterDamageCalculationEvents, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "after_damage_calculation"
        super(AfterDamageCalculationEvents,self).run(gamestate)

class EndOfDamageStepEvents(DamageStepEventAction):
    def init(self, ds_action):
        super(EndOfDamageStepEvents, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "end"
        super(EndOfDamageStepEvents,self).run(gamestate)


class BattleSendsMonstersToGraveyard(Action):
    def init(self, ds_action):
        self.ds_action = ds_action
        self.args = ds_action.args

    def run(self, gamestate):
        list_of_steps = []
        counter = 0
        for monster in gamestate.monsters_to_be_destroyed_by_battle:
            gamestate.monsters_to_be_destroyed_by_battle.remove(monster)
            if monster.location == "Field":
                self.args['monster' + str(counter)] = monster
                list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, DestroyMonsterByBattle, 'monster' + str(counter)))
            
            counter += 1

        self.run_steps(gamestate, list_of_steps)

class DestroyMonsterByBattle(Action):
    def init(self, card):
        super().init('Destroy monster by battle', card)
        self.args = {'monster' : card, 'ccz_type' : CCZDESTROY, 'cause' : CAUSE_BATTLE, 'IsContained' : True, 'parent_effect' : None}
    
    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.InitAndRunAction(self, ChangeCardZone, 'ccz_type', 'monster', 'cause', 'parent_effect', 'IsContained'),
                        #engine.HaltableStep.AppendToLRAIfRecording(self),
                        #engine.HaltableStep.ProcessTriggerEvents(self),
                        #engine.HaltableStep.RunImmediateEvents(self),
                        engine.HaltableStep.PopActionStack(self)]
        
        self.run_steps(gamestate, list_of_steps)


class CeaseDuringDamageStepEffects(DamageStepEventAction):
    def init(self, ds_action):
        super(CeaseDuringDamageStepEffects, self).init(ds_action)

    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.RunImmediateEvents(self)]

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()


class LaunchEndStep(Action):
    def run(self, gamestate):
        self.args = {}
        gamestate.current_battle_phase_step = 'end_step'
        list_of_steps = [engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_end_step'),
                         engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'battle_phase_end_step'),
                         engine.HaltableStep.SetAttackDeclaredActionToNone(self),
                         engine.HaltableStep.LetTurnPlayerChooseNextPhase()]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

