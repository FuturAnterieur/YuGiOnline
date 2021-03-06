import engine.HaltableStep
from engine.defs import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE, FACEUPTOOPPONENT, CCZTRIBUTE, CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, CAUSE_BATTLE, CAUSE_CHAIN, CAUSE_TRIBUTE

class Action:
    def init(self, name, card, parent_effect = None):
        self.name = name
        self.card = card
        self.parent_effect = parent_effect
        if card is not None:
            self.player = card.owner
        self.was_negated = False
        
    def check_for_bans(self, gamestate):
        unbanned = True
        for ban in gamestate.bans:
            if ban.bans_action(self, gamestate):
                unbanned = False
                break

        return unbanned

    def check_for_blocks(self, card, gamestate):
        compatible = True
        for effect in card.effects:
            if effect.blocks_action(self, gamestate):
                compatible = False
                break

        return compatible

    def check_for_bans_and_blocks(self, card, gamestate):
        return self.check_for_bans(gamestate) and self.check_for_blocks(card, gamestate) 

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
        #in_timing_optional_fast_respond_events are cleared after each of these steps automatically.
        
        step2 = engine.HaltableStep.OpenWindowForResponse(self, 'response_window:' + self.event_type, 'firstplayer', 'FirstplayerUsesRW')
        step3 = engine.HaltableStep.RunStepIfCondition(self, 
                engine.HaltableStep.OpenWindowForResponse(self, 'response_window:' + self.event_type, 'secondplayer', 'SecondplayerUsesRW'), 
                RunOtherPlayerWindowCondition, 'FirstplayerUsesRW')
        
        list_of_steps = [step2, step3]

        self.run_steps(gamestate, list_of_steps)

class RunExclusiveResponseWindows(Action):
    def init(self, firstplayer, event_type, action_to_match):
        self.args = {}
        self.args['firstplayer'] = firstplayer
        self.args['secondplayer'] = firstplayer.other
        self.event_type = event_type
        self.args['action_to_match'] = action_to_match

    def run(self, gamestate):
        step2 = engine.HaltableStep.OpenWindowForExclusiveResponse(self, 'response_window:' + self.event_type, 'action_to_match', 'firstplayer', 'FirstplayerUsesRW')
        step3 = engine.HaltableStep.RunStepIfCondition(self, 
                engine.HaltableStep.OpenWindowForExclusiveResponse(self, 'response_window:' + self.event_type, 
                                                                    'action_to_match', 'secondplayer', 'SecondplayerUsesRW'), 
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

def CheckIfNotNegated(gamestate, args, action_arg_name):
    action = args[action_arg_name]
    return not action.was_negated


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

        engine.HaltableStep.clear_in_timing_optional_fast_trigger_events(gamestate)
        #it's important to clear them beforehand so that the optional fast trigger events 
        #that were in_timing in the previous chain are not in_timing in the new one.
        engine.HaltableStep.refresh_in_timing_optional_fast_trigger_events(gamestate) 
        engine.HaltableStep.clear_in_timing_respond_OFast_LRA(gamestate)
        engine.HaltableStep.refresh_in_timing_respond_OFast_LRA(gamestate)
       
        engine.HaltableStep.refresh_SEGOC_events(gamestate)
        
        #respond_OFast (like Trap Hole) and optional fast triggers (like That Wacky Alchemy) 
        #won't be put on the SEGOC chain, but they can be chained afterwards
        #(either on top of the SEGOC effects or by starting a chain of their own if no SEGOC chain is formed)

        #Hence, their associated action's reqs will be checked at the time of checking which actions can be chained
        #at each point in the chain link.

        #in contrast, SEGOC events don't have a chance to get their reqs checked at the time of being put 
        #in the SEGOC list, so their reqs need to be checked in the following line.

        engine.HaltableStep.refresh_SEGOC_events_meeting_reqs(gamestate)
        
        list_of_steps = []


        for trigger in gamestate.events_meeting_reqs['trigger_MSS1TP'] + gamestate.events_meeting_reqs['respond_MSS1TP']:
            #if there is more than one trigger in a category and we are building a SEGOC chain, 
            #which we will always be doing since we are at the end of a previous chain, ask the player 
            #who owns the effects how he wants to order them in the chain
            gamestate.triggers_to_run.append(trigger)

        for trigger in gamestate.events_meeting_reqs['trigger_MSS1OP'] + gamestate.events_meeting_reqs['respond_MSS1OP']: #meme principe pour les autres
            gamestate.triggers_to_run.append(trigger)

        for trigger in gamestate.events_meeting_reqs['trigger_OSS1TP'] + gamestate.events_meeting_reqs['respond_OSS1TP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'turnplayer'))

        for trigger in gamestate.events_meeting_reqs['trigger_OSS1OP'] + gamestate.events_meeting_reqs['respond_OSS1OP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'otherplayer'))


        
        #what happens when an optional effect is triggered and scheduled for a SEGOC chain?
        #the choice is given to the player to activate the effect or not,
        #and then, if there is more than one trigger in the category,
        #the player who owns them decides in which order they get stacked on the chain
        #(same principle as for mandatory effects).
        
        #then run the chain
        
        #at the end I do something almost equivalent to RunResponseWindows, but without engine.HaltableStep.ProcessMandatoryRespondEvents(self),
        #since those will only have an effect if there is already something in the gamestate.chainlinks stack and, in our case here, there is nothing
        #in the SEGOC triggers_to_run container.

        #well, according to how those MandatoryRespondEvents seem to work up to now, at least.
        #I don't know if they can be activated in response to LastResolvedActions too.

        list_of_steps.extend([engine.HaltableStep.ClearSEGOCInTimingEvents(self),
                                #we don't need those, they were all transferred to triggers_to_run (if there were any)
                                engine.HaltableStep.ClearSavedTriggerEvents(self), 
                                #we don't need those too, they were all transferred to events_in_timing
                                engine.HaltableStep.RunStepIfElseCondition(self, 
                                        engine.HaltableStep.LaunchTTR(self),
                                        engine.HaltableStep.InitAndRunAction(self, RunOptionalResponseWindows, 'turnplayer', 'for_what_event'),
                                        TTRNonEmpty),
                                engine.HaltableStep.ClearInTimingOptionalFastTriggerEvents(self),
                                engine.HaltableStep.ClearInTimingOptionalFastRespondEventsLRA(self)]) 
                                #these were built at the start of the current call to RunEvents
                                #the Clear as an ending step is to clear them at the exit of all the 
                                #calls to RunEvents that might have happened.
        
        if (self.at_end_of_events):
            list_of_steps.append(engine.HaltableStep.LowerOuterActionStackLevel(self))
        
        #the same structure of If-Else LaunchTTR vs RunOptionalResponseWindows can be used inside the Actions that constitute chain links

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
        
        self.run_steps(gamestate, list_of_steps)

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

class RemoveAcquiredModifiers(Action):
    def init(self, card, zone):
        super().init('Utility effect deactivation for leaving ' + zone.type, card)
        self.args = {}
        self.zone = zone
        self.card = card

    def default_run(self, gamestate):
        los = steps_for_event_pre_action(self, gamestate)
        self.run_steps(gamestate, los)

        # basically what it should do is this
        if self.zone.type == "Field":
            for parameter in self.card.parameters:
                modifiers_to_remove = []
                for modifier in parameter.local_modifiers:
                    if modifier.lost_when_leave_field or modifier.was_gained:
                        modifiers_to_remove.append(modifier)

                for modifier in modifiers_to_remove:
                    parameter.local_modifiers.remove(modifier)

            ccz_mods_to_remove = []
            for modifier in self.card.CCZModifiers:
                if modifier.was_gained:
                    ccz_mods_to_remove.append(modifier)

            for mod in ccz_mods_to_remove:
                self.card.CCZModifiers.remove(mod)


            

    run_func = default_run

        


#attempt to merge Destroy, Banish, Discard and Return To Hand in a single, at-run-time modifiable action

def DestinationIsGYOrBanished(gamestate, args, tozone_arg_name):
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
        self.args = {'card' : card, 'fromzone' : card.zone, 'tozone' : tozone, 'this_action' : self, 'owner' : card.owner, 'other' : card.owner.other}
        self.is_contained = is_contained
        self.with_leave_zone_trigger = with_leave_zone_trigger
        self.parent_effect = parent_effect
    
    def get_pre_steps(self):

        clear_lra_step = engine.HaltableStep.DoNothing(self) if self.is_contained else engine.HaltableStep.ClearLRAIfRecording(self)
        los = [clear_lra_step,
                engine.HaltableStep.InitAndRunAction(self, TurnOffPassiveEffects, 'card', 'fromzone'),
                engine.HaltableStep.InitAndRunAction(self, RemoveAcquiredModifiers, 'card', 'fromzone')]

        return los

    def get_main_steps(self):
        lzt_step = engine.HaltableStep.InitAndRunAction(self, CardLeavesZoneEvents, 'card', 'fromzone') if self.with_leave_zone_trigger else engine.HaltableStep.DoNothing(self)
        los = [engine.HaltableStep.ProcessCCZModifiers(self),
                            engine.HaltableStep.RunStepIfCondition(self, 
                                    engine.HaltableStep.ChangeCardVisibility(self, ['owner', 'other'], 'card', "1"),
                                    DestinationIsGYOrBanished, 'tozone'),
                            engine.HaltableStep.MoveCard(self, 'card', 'tozone'),
                            engine.HaltableStep.RunStepIfCondition(self, 
                                    engine.HaltableStep.EraseCard(self, 'card'),
                                    DestinationIsGYOrBanished, 'tozone'),
                            engine.HaltableStep.ChangeCardZoneServer(self, 'card', 'tozone'),
                            lzt_step,
                            engine.HaltableStep.InitAndRunAction(self, CardSentToZoneEvents, 'card', 'tozone'),
                            engine.HaltableStep.ProcessTriggerEvents(self),
                            engine.HaltableStep.AppendToLRAIfRecording(self),
                            engine.HaltableStep.RunImmediateEvents(self)]
        return los

    
    def default_run(self, gamestate):
        
        clear_lra_step = engine.HaltableStep.DoNothing(self) if self.is_contained else engine.HaltableStep.ClearLRAIfRecording(self)
        lzt_step = engine.HaltableStep.InitAndRunAction(self, CardLeavesZoneEvents, 'card', 'fromzone') if self.with_leave_zone_trigger else engine.HaltableStep.DoNothing(self)
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                            clear_lra_step,
                            engine.HaltableStep.InitAndRunAction(self, TurnOffPassiveEffects, 'card', 'fromzone'),
                            engine.HaltableStep.InitAndRunAction(self, RemoveAcquiredModifiers, 'card', 'fromzone'),
                            #for deactivating cards when they leave the field, mostly
                            engine.HaltableStep.ProcessCCZModifiers(self),
                            engine.HaltableStep.RunStepIfCondition(self, 
                                    engine.HaltableStep.ChangeCardVisibility(self, ['owner', 'other'], 'card', "1"),
                                    DestinationIsGYOrBanished, 'tozone'),
                            engine.HaltableStep.MoveCard(self, 'card', 'tozone'),
                            engine.HaltableStep.RunStepIfCondition(self, 
                                    engine.HaltableStep.EraseCard(self, 'card'),
                                    DestinationIsGYOrBanished, 'tozone'),
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

class GroupCCZ(Action):
    def init(self, name, cards, cause, parent_effect = None, is_contained = False, with_leave_zone_trigger = True):
        
        self.intended_action = name
        self.intended_tozone = tozone 
        self.args = {'this_action' : self}
        
        self.num_cards = len(cards)

        self.cards = cards
        
        self.is_contained = is_contained
        self.with_leave_zone_trigger = with_leave_zone_trigger
        self.parent_effect = parent_effect
        self.cause = cause

    def default_run(self, gamestate):
        #TurnOffPassiveEffects and RemoveAcquiredModifiers for all cards before all cards are sent elsewhere
        clear_lra_step = engine.HaltableStep.DoNothing(self) if self.is_contained else engine.HaltableStep.ClearLRAIfRecording(self)
        
        los = [engine.HaltableStep.AppendToActionStack(self), clear_lra_step]
        ccz_actions = []

        for i in range(self.num_cards):
            ccz_actions.append(ChangeCardZone())
            ccz_actions[-1].init(self.name, self.cards[i], self.cause, self.parent_effect, True, self.with_leave_zone_trigger)
        
        for i in range(self.num_cards):
            los.extend(ccz_actions[i].get_pre_steps())

        for i in range(self.num_cards):
            los.extend(ccz_actions[i].get_main_steps())

        los.extend([engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.RunAction(self, RunEvents(self.name)), RunEventsCondition),
                            engine.HaltableStep.PopActionStack(self),
                            engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)])

        self.run_steps(gamestate, los)

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


class Target(Action):
    def init(self, card, list_of_possible_targets, parent_effect = None, target_arg_name_for_effect = None):
        super().init('Target', card)
        self.args = {'player' : self.card.owner, 'possible_targets' : list_of_possible_targets, 'chosen_target' : None, 'parent_effect' : parent_effect}
        self.parent_effect = parent_effect
        self.target_arg_name_for_effect = None
        if self.parent_effect is not None and target_arg_name_for_effect is not None:
             self.target_arg_name_for_effect = target_arg_name_for_effect
    
    def run(self, gamestate):
        set_effect_step = engine.HaltableStep.DoNothing(self)
        
        if self.target_arg_name_for_effect is not None:
            set_effect_step = engine.HaltableStep.SetArgInEffectToValue(self, 'parent_effect', self.target_arg_name_for_effect, 'chosen_target') 

        list_of_steps = [engine.HaltableStep.ChooseOccupiedZone(self, 'player', 'possible_targets', 'chosen_target'),
                        set_effect_step]
        list_of_steps.extend(steps_for_event_action(self, gamestate))
        self.run_steps(gamestate, list_of_steps)


class FlipMonsterFaceUp(Action):
    def init(self, card):
        super().init("Flip monster face up", card)
        self.args = {'monster' : card, 'player1' : card.owner, 'player2' : card.owner.other}

    def run(self, gamestate):
        
        
        
        #no ClearLRA because this will always be a sub-action
        list_of_steps = [engine.HaltableStep.ChangeCardVisibility(self, ['player1', 'player2'], 'monster', "1"),
                        engine.HaltableStep.InitAndRunAction(self, ProcessFlipEvents, 'monster')]

        #flip effects in a summon situation :
        #they will be added to the saved if-triggers 
        #and will thus be triggered during the SEGOC chain building at the end of the summon.

        #in a battle situation,
        #the RunImmediateEvents will add an if-trigger that triggers at AfterDamageCalculation

        #so a flip trigger's category is 'if' (either mandatory or optional), but it goes in the gamestate.flip_events container.
        
        self.run_steps(gamestate, list_of_steps)


class ProcessFlipEvents(Action):
    def init(self, card):
        super().init("Monster flipped face up", card)
        self.args = {'monster' : card}

    def run(self, gamestate):
        
        self.args['monster'].face_up = FACEUPTOEVERYONE
        list_of_steps = [engine.HaltableStep.ProcessFlipEvents(self)]
        self.run_steps(gamestate, list_of_steps)



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
        super().init("Attack replay", parent_declare_attack_action.card)
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

In BattleStepBranchOut we also evaluate if the attacker can still attack. If he can't, we reset the battle step.

"""

def AttackerStillOnFieldInAttackPosition(gamestate, args):
    attacker = gamestate.attack_declared_action.card
    return attacker.location == "Field" and attacker.position == "ATK"

class BattleStepBranchOut(Action):
    def run(self, gamestate):
        self.args = {}
        list_of_steps = []

        gamestate.immediate_events.remove(gamestate.AttackReplayTrigger)

        if gamestate.attack_declared == True:
            self.args['ad_action'] = gamestate.attack_declared_action
            
            if AttackerStillOnFieldInAttackPosition(gamestate, self.args):
                if AttackTargetingReplayCondition(gamestate, self.args):
                    list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, AttackTargetingReplay, 'ad_action'))
                
                else:
                    list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, LaunchDamageStep, 'ad_action'))

                
            else:
                list_of_steps.extend([engine.HaltableStep.CancelAttackInGamestate(self),
                                      engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step'),
                                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'battle_phase_battle_step'), 
                                        engine.HaltableStep.RunAction(self, engine.Action.BattleStepBranchOut())])                                       

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
                        engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.InitAndRunAction(self, StartOfDamageStepEvents, 'this_action'), 
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_start', False)), 
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_start'),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_start'),
                        engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.InitAndRunAction(self, BeforeDamageCalculationEvents, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_BDC', False)), 
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
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
            #as having to be added to in_timing_optional_respond_events at AfterDamageCalculation.
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
                        engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.InitAndRunAction(self, AfterDamageCalculationEvents, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_ADC', False)), 
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_ADC'),
                        #engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_ADC'),
                        engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.InitAndRunAction(self, BattleSendsMonstersToGraveyard, 'this_action'),
                        engine.HaltableStep.InitAndRunAction(self, EndOfDamageStepEvents, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunEvents('damage_step_end', False)),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
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
        self.name = "DuringDamageCalculation"
        self.ds_action = ds_action
        self.args = ds_action.args

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "during_damage_calculation"
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.RunImmediateEvents(self),
                        engine.HaltableStep.ProcessTriggerEvents(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self),
                        engine.HaltableStep.RunAction(self, RunEvents('during damage calculation', False)),
                        engine.HaltableStep.PopActionStack(self),
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
        self.name = "MonstersMarkedEventsForAll"
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
        super(MonsterMarkedEvents, self).init('Monster determined to be destroyed', card)
        self.args = {}

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
        self.name = "Battle sends monsters to graveyard"
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



