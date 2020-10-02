from engine.CardModel import NormalTrapCardModel
from engine.Effect import Effect
import engine.Action
from engine.Event import Event
import engine.Bans

from engine.defs import CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, STATE_NOTINEFFECT, STATE_EVENT, STATE_ACTIVATE, STATE_RESOLVE, CAUSE_EFFECT


class TrapHoleEffect(Effect):
    def __init__(self):
        super(TrapHoleEffect, self).__init__("TrapHoleEffect", "Trap")
        
    def init(self, gamestate, card):
        super().init(card)
        self.was_negated = False
        self.spellspeed = 2
        self.SummonedMonster = None

        self.potential_targets = []

        self.effect_event = Event("TrapHoleEvent", self.parent_card, self, "respond", "OFast", self.MatchOnTHCompatibleSummon)
        self.effect_event.funclist.append(self.LaunchNormalTrapActivationForTH)

        self.set_event = Event("TrapHoleOnSet", self.parent_card, self, "immediate", "", self.MatchOnTHSet)
        self.set_event.funclist.append(self.TurnOnTHEvent)

        self.leaves_field_event = Event("TrapHoleOnLeaveField", self.parent_card, self, "immediate", "", self.MatchTHTurnOff)
        self.leaves_field_event.funclist.append(self.TurnOffTHEvent)

        gamestate.immediate_events.append(self.set_event)
        gamestate.immediate_events.append(self.leaves_field_event)

    def MatchOnTHSet(self, action, gamestate):
        return action.__class__.__name__ == "SetSpellTrap" and action.card == self.parent_card

    def TurnOnTHEvent(self, gamestate):
        gamestate.respond_events.append(self.effect_event)

    def MatchTHTurnOff(self, action, gamestate):
        return action.__class__.__name__ == "TurnOffPassiveEffects" and action.zone.type == "Field" and action.card == self.parent_card
        #if it was a CardLeavesZoneEvents, it wouldn't work in all cases, because if an effect is negated, 
        #the destruction of its card does not call a CardLeavesZoneEvents step


    def TurnOffTHEvent(self, gamestate):
        if (self.effect_event in gamestate.respond_events):
            gamestate.respond_events.remove(self.effect_event)


    def MatchOnTHCompatibleSummon(self, action, gamestate):
        result = False
        if action.name == "Normal Summon Monster" and action.card.face_up == True and action.card.attack >= 1000:

            #do the check for the Activate's Target action too
            print("MatchOnTHCompatible found valid target. Checking immunities...")
            HypotheticalDestroyAction = engine.Action.ChangeCardZone()
            HypotheticalDestroyAction.init(engine.Action.CCZDESTROY, action.card, False, self)
            if HypotheticalDestroyAction.check_for_bans_and_immunities(action.card, gamestate, STATE_EVENT):
                print("Immunity test passed. Target is valid.")
                result = True
                self.potential_targets.append(action.card)

        return result

    def LaunchNormalTrapActivationForTH(self, gamestate):
        self.card.actiondict["Activate"].run(gamestate)

    def reqs(self, gamestate):
        #Trap card immunity as well as Targeting/Destroying bans are implemented in the MatchOnTHCompatibleSummon function

        return self.effect_event.is_in_chainable_events(gamestate)

        #Trap Hole actually works through the summon response window (but not the summon negation window) 
        #AND the summon response window will work through lastresolvedactions 
         
    def Activate(self, gamestate):
        #choose the target if many choices are possible (which would only happen if 
        #many monsters are summoned at once, which I am not even sure is possible)
        
        #Actually, according to the card text, only one target is possible (if another monster is summoned,
        #the first one misses the timing, I think).  

        self.TargetedMonster = self.potential_targets[0]
        self.potential_targets.clear()
        
    def Resolve(self, gamestate):
        if self.TargetedMonster is not None:
            self.current_state_for_checks = STATE_RESOLVE

            DestroyAction = engine.Action.ChangeCardZone()
            DestroyAction.init(engine.Action.CCZDESTROY, self.TargetedMonster, CAUSE_EFFECT, self, False, True)
        
            if DestroyAction.check_for_bans_and_immunities(self.TargetedMonster, gamestate, STATE_RESOLVE):
                DestroyAction.run(gamestate)


TrapHole = NormalTrapCardModel("Trap Hole",  "Dump a monster with 1000 or more ATK", 'trap_hole.jpg', TrapHoleEffect)

