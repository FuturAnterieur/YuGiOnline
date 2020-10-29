
from engine.Action import Action, ChainSendsToGraveyard, RunResponseWindows, RunEvents, RunMAWsAtEnd, ActionStackEmpty, EndOfChainCondition, RunEventsCondition, TTRNonEmpty, CheckIfNotNegated

import engine.HaltableStep  

from engine.defs import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE, FACEUPTOOPPONENT

class SetSpellTrap(Action):
    
    def init(self, card):
        super().init("Set Spell/Trap card", card)
        self.player = card.owner
        self.args = {'set_card' : card, 'chosen_zone' : None, 'player' : self.player}
        
        self.list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.ChooseFreeZone(self, 'player', 'zone_choices', 'chosen_zone'),
                        engine.HaltableStep.SetSpellTrapServer(self, 'set_card', 'chosen_zone'),
                        engine.HaltableStep.MoveCard(self, 'set_card', 'chosen_zone'),
                        engine.HaltableStep.ChangeCardVisibility(self, ['player'], 'set_card', "0"),
                        engine.HaltableStep.ProcessTriggerEvents(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self),
                        engine.HaltableStep.RunImmediateEvents(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunEvents('Spell/Trap set')), 
                            RunEventsCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]


    def reqs(self, gamestate):
        if self.check_for_bans(gamestate) == False:
            return False

        if self.player != gamestate.turnplayer or (gamestate.curphase != 'main_phase_1' and gamestate.curphase != 'main_phase_2'):
            return False

        if len(gamestate.action_stack) > 0:
            return False

        if self.card.location != "Hand":
            return False

        if len(self.player.spelltrapzones.occupiedzonenums) == 5:
            return False

        return True

    def default_run(self, gamestate):
        self.args['zone_choices'] = [zone for zone in self.card.owner.spelltrapzones.listofzones 
                                        if zone.zonenum not in self.card.owner.spelltrapzones.occupiedzonenums]


        self.run_steps(gamestate)
                        

    run_func = default_run



def get_spelltrap_resolve_steps(action, chain_sends_to_graveyard = True):

    cstg_step = engine.HaltableStep.DoNothing(action)
    if chain_sends_to_graveyard:
        cstg_step = engine.HaltableStep.RunStepIfCondition(action,
                                        engine.HaltableStep.AddCardToChainSendsToGraveyard(action, 'card'),
                                        CheckIfCardOnField, 'card')

         #cards which have had their activation negated are considered as not being on the field for other effects' purposes.
                         #but for the ChainSendsToGraveyard, they should be considered as being on the field.

    list_of_steps = [engine.HaltableStep.UnsetBuildingChain(action),
                         engine.HaltableStep.PopChainLinks(action),
                         engine.HaltableStep.RunStepIfCondition(action, 
                                        engine.HaltableStep.InitAndRunAction(action, ResolveEffectCore, 'card', 'effect'),
                                        CheckIfNotNegated, 'this_action'),
                         cstg_step, 
                         engine.HaltableStep.RunStepIfCondition(action, 
                                                engine.HaltableStep.RunAction(action, ChainSendsToGraveyard()), EndOfChainCondition),
                         engine.HaltableStep.RunStepIfCondition(action, engine.HaltableStep.RunAction(action, RunEvents('Chain resolved')), RunEventsCondition),
                         engine.HaltableStep.PopActionStack(action),
                         engine.HaltableStep.RunStepIfCondition(action, engine.HaltableStep.RunAction(action, RunMAWsAtEnd()), ActionStackEmpty)]

    return list_of_steps

def CheckIfCardOnField(gamestate, args, card_arg_name):
    card = args[card_arg_name]
    return card.location == "Field" or card.location == "Field_Activation_Negated"
    

def CheckIfCardInHand(gamestate, args, card_arg_name):
    card = args[card_arg_name]
    return card.location == "Hand"




class ActivateNormalOrQuickPlaySpell(Action):

    def init(self, card, effect):
        super().init("Activate Normal or Quick-Play Spell", card)
        self.effect = effect
        self.player = card.owner
        self.args = {'this_action' : self, 'card' : card, 'effect' : effect, 'actionplayer' : card.owner, 
                'otherplayer' : card.owner.other, 'action_name' : card.spelltype + ' Spell activated', 'chosen_zone' : None}

    def reqs(self, gamestate):
        if self.check_for_bans(gamestate) == False:
            return False

        if gamestate.curphase == "standby_phase":
            return False

        if self.card.face_up == FACEUPTOEVERYONE:
            #this is equivalent to a 'once per chain' constraint
            return False

        if self.card.location == "Hand" and len(self.player.spelltrapzones.occupiedzonenums) == 5:
            return False

        if self.card.spelltype == "Normal" and (gamestate.curphase == "battle_phase" 
                or gamestate.turnplayer != self.player or len(gamestate.action_stack) > 0):
            return False

        if self.card.spelltype == "Quick-Play" and ((gamestate.turnplayer != self.player and self.card.location == "Hand") 
                or gamestate.current_battle_phase_step == "damage_step" or gamestate.curspellspeed > 2 
                or (self.card.location == "Field" and self.card.wassetthisturn)):
            return False

        if self.effect.reqs(gamestate) == False:
            return False

        return True

    def run(self, gamestate):

        self.args['zone_choices'] = [zone for zone in self.card.owner.spelltrapzones.listofzones 
                                        if zone.zonenum not in self.card.owner.spelltrapzones.occupiedzonenums]

        place_card_on_field_step = engine.HaltableStep.DoNothing(self)

        if self.card.location == "Hand":
            place_card_on_field_step = engine.HaltableStep.InitAndRunAction(self, ChooseZoneAndMoveSpell, 'this_action')
        
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.SetBuildingChain(self),
                         place_card_on_field_step, 
                         engine.HaltableStep.ActivateSpellTrapBeforeActivate(self, 'card', 'effect', 'chosen_zone'),
                         engine.HaltableStep.ChangeCardVisibility(self, ['otherplayer', 'actionplayer'], 'card', "1"),
                         engine.HaltableStep.AppendToChainLinks(self),
                         engine.HaltableStep.DisableLRARecording(self),
                         engine.HaltableStep.CallEffectActivate(self, 'effect'),
                         engine.HaltableStep.EnableLRARecording(self),
                         engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'otherplayer', 'action_name')] + get_spelltrap_resolve_steps(self)



        self.run_steps(gamestate, list_of_steps)

class ChooseZoneAndMoveSpell(Action):
    def init(self, parentAction):
        self.parentAction = parentAction
        self.args = self.parentAction.args

        self.list_of_steps = [engine.HaltableStep.ChooseFreeZone(self, 'actionplayer', 'zone_choices', 'chosen_zone'),
                                engine.HaltableStep.MoveCard(self, 'card', 'chosen_zone')]

    def run(self, gamestate):
        self.run_steps(gamestate)


    
def basic_reqs_for_trap(action, gamestate):
    if gamestate.curspellspeed > action.effect.spellspeed:
        return False

    if action.card.location != "Field":
        return False

    if action.card.wassetthisturn == True:
        return False

    if gamestate.curphase == "standby_phase":
        return False

    return True

class ActivateNormalTrap(Action):
    
    def init(self, card, effect):
        super().init("Activate Normal Trap", card)
        self.effect = effect
        self.args = {'this_action' : self, 'card' : card, 'effect' : effect, 'actionplayer' : card.owner, 
                        'otherplayer' : card.owner.other, 'action_name' : 'Normal trap activated'}

        self.list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.SetBuildingChain(self),
                         engine.HaltableStep.ActivateSpellTrapBeforeActivate(self, 'card', 'effect'),
                         engine.HaltableStep.ChangeCardVisibility(self, ['otherplayer', 'actionplayer'], 'card', "1"),
                         engine.HaltableStep.AppendToChainLinks(self),
                         engine.HaltableStep.DisableLRARecording(self),
                         engine.HaltableStep.CallEffectActivate(self, 'effect'),
                         engine.HaltableStep.EnableLRARecording(self),
                         engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'otherplayer', 'action_name')] + get_spelltrap_resolve_steps(self)
                         

    def reqs(self, gamestate):
        if self.check_for_bans(gamestate) == False:
            return False
        
        if basic_reqs_for_trap(self, gamestate) == False:
            return False

        if self.effect.reqs(gamestate) == False:
            return False

        if self.card.face_up != FACEDOWN: #or I could put a 'once per chain' constraint
            return False

        return True
    
    def default_run(self, gamestate):
        self.run_steps(gamestate)
                         
    run_func = default_run

class ActivateContinuousTrap(Action):
    def init(self, card, effect):
        super().init("Activate Continuous Trap", card)
        self.effect = effect
        self.args = {'this_action' : self, 'card' : card, 'effect' : effect, 'actionplayer' : card.owner, 
                        'otherplayer' : card.owner.other, 'action_name' : 'Normal trap activated'}

        self.list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.SetBuildingChain(self),
                         engine.HaltableStep.ActivateSpellTrapBeforeActivate(self, 'card', 'effect'),
                         engine.HaltableStep.ChangeCardVisibility(self, ['otherplayer', 'actionplayer'], 'card', "1"),
                         engine.HaltableStep.AppendToChainLinks(self),
                         engine.HaltableStep.DisableLRARecording(self),
                         engine.HaltableStep.CallEffectActivate(self, 'effect'),
                         engine.HaltableStep.EnableLRARecording(self),
                         engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'otherplayer', 'action_name')] + get_spelltrap_resolve_steps(self, False)

    def reqs(self, gamestate):
        if self.check_for_bans(gamestate) == False:
            return False
        
        if basic_reqs_for_trap(self, gamestate) == False:
            return False

        if self.effect.reqs(gamestate) == False:
            return False

        if self.card.face_up != FACEDOWN: #or I could put a 'once per chain' constraint
            return False

        return True

    def default_run(self, gamestate):
        self.run_steps(gamestate)

    run_func = default_run

class ResolveEffectCore(Action):
    def init(self, card, effect):
        super().init("Activate Normal Trap", card)
        self.effect = effect
        self.args = {'effect' : effect}

    
    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.ClearLRAIfRecording(self),
                         engine.HaltableStep.ProcessTriggerEvents(self),
                         engine.HaltableStep.RunImmediateEvents(self), #for 'an effect is resolving' (see Abyss-scale of the Kraken)
                         engine.HaltableStep.CallEffectResolve(self, 'effect'), #the Effect Resolve will call its own trigger-setting steps
                         engine.HaltableStep.AppendToLRAIfRecording(self)] 
                         #engine.HaltableStep.ProcessTriggerEvents(self),
                         #engine.HaltableStep.AppendToLRAIfRecording(self), #for the actual action of resolving the card
                         #engine.HaltableStep.RunImmediateEvents(self)]

        self.run_steps(gamestate, list_of_steps)

