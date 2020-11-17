from engine.Effect import Effect, MatchTurnSwitch
import engine.Action
from engine.Parameter import UnaffectedModifier
from engine.Cards import QuickPlaySpellCard
from engine.Event import Event

from engine.defs import FACEUPTOEVERYONE, STATE_ACTIVATE

class ForbiddenLanceEffect(Effect):
    def __init__(self, gamestate, card):
        super().__init__("ForbiddenLanceEffect", "Quick-Spell", card)
        self.spellspeed = 2
        self.args = {'potential_targets' : [], 'targeted_monster' : None}

        self.ForbiddenLanceUnaff = UnaffectedModifier(self, None, self.unaffected_by_other_st, False)
        
        self.EndOfTurnEvent = Event("ForbiddenLanceEndOfTurn", self.parent_card, self, 
                                            None, "immediate", "", MatchTurnSwitch)
        self.EndOfTurnEvent.funclist.append(self.ForbiddenLanceCleanup)
        #at end of turn

    def ForbiddenLanceCleanup(self, gamestate):
        self.args['targeted_monster'].unaffected.local_modifiers.remove(self.ForbiddenLanceUnaff)
        gamestate.phase_transition_events['turn_switch'].remove(self.EndOfTurnEvent)
        

    def unaffected_by_other_st(self, effect, gamestate):
        unaffected = False
        if effect.parent_card.cardclass == "Spell/Trap" and effect.parent_card != self.parent_card:
            unaffected = True

        return unaffected

    def reqs(self, gamestate):
        self.args['potential_targets'].clear()
        fu_monsters_on_field = [card for card in gamestate.yugi.monsters_on_field + gamestate.kaiba.monsters_on_field if card.face_up == FACEUPTOEVERYONE]
        for card in fu_monsters_on_field:
            HypotheticalTargetAction = engine.Action.Target()
            HypotheticalTargetAction.init(self.parent_card, [], self, 'targeted_monster')
            HypotheticalTargetAction.args['chosen_target'] = card

            #Hypothetical "Make target unaffected and lose ATK" action?

            action_desc_list = [{'action': HypotheticalTargetAction, 'card':card, 'in_activate_or_resolve': STATE_ACTIVATE}]

            if self.check_if_activation_is_allowed(action_desc_list, gamestate):
                self.args['potential_targets'].append(card)


        return len(self.args['potential_targets']) > 0

    def Activate(self, gamestate):
        TargetAction = engine.Action.Target()
        TargetAction.init(self.parent_card, self.args['potential_targets'], self, 'targeted_monster')
        TargetAction.run(gamestate)

    def check_if_target_is_still_valid(self):
        return self.args['targeted_monster'].location == "Field" and self.args['targeted_monster'].face_up == FACEUPTOEVERYONE

    def Resolve(self, gamestate):
        if self.is_negated.get_value(gamestate) == False and self.affects_card(self.args['targeted_monster'], gamestate) and self.check_if_target_is_still_valid():
            
            self.args['targeted_monster'].unaffected.local_modifiers.append(self.ForbiddenLanceUnaff)

            gamestate.phase_transition_events['turn_switch'].append(self.EndOfTurnEvent)

    
class ForbiddenLance(QuickPlaySpellCard):
    def __init__(self, ID, owner, gamestate):
        super().__init__("Forbidden Lance", "Target 1 face-up monster on the field; until the end of this turn, that target loses 800 ATK, but is unaffected by the effects of other Spells/Traps.", "forbidden_lance.jpg", ForbiddenLanceEffect, ID, owner, gamestate)


