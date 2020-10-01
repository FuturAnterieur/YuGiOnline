
import engine.Action
import engine.HaltableStep
from engine.Event import Event
import engine.Bans

from engine.defs import CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, STATE_NOTINEFFECT, STATE_EVENT, STATE_ACTIVATE, STATE_RESOLVE, CAUSE_EFFECT

class Effect:
    def __init__(self, name, etype):
        self.name = name
        self.type = etype
        
        self.ActivateActionInfoList = []
        self.ResolveActionLInfoList = []

    def init(self, parent_card):
        self.parent_card = parent_card

    def blocks_action(self, action, effect_state = STATE_NOTINEFFECT):
        return False


class PassiveEffect(Effect):
    def __init__(self, name, etype):
        super().__init__(self, name, etype)
        self.is_dormant = False
        self.is_negated = False
        self.is_on = False
        
    def init(self, parent_card):
        super().init(self, parent_card)

    def Negate(self, gamestate):
        if self.is_on:
            self.TurnOff(gamestate)
            self.is_dormant = True

        self.is_negated = True

    def UnNegate(self, gamestate):
        self.is_negated = False
        if self.is_dormant:
            self.is_dormant = False
            self.TurnOn(gamestate) 


def MatchOnADC(action, gamestate):
    return action.__class__.__name__ == "AfterDamageCalculationEvents"

class FlipEffect(Effect):
    def __init__(self, name, etype, parent_card):
        super(FlipEffect, self).__init__(name, etype, parent_card)
        self.ADC_event = None

    def RemoveADCEventFromTriggerEvents(self, gamestate):
        gamestate.trigger_events.remove(self.ADC_event)

class UnaffectedByTrap(Effect):
    def __init__(self):
        super().__init__("ImmuneToTrap", "Immune")
    
    def init(self, gamestate, card):
        self.card = card
        self.is_negated = False

    def blocks_action(self, action, effect_state = STATE_NOTINEFFECT):
        #Allow events to match and activation actions to proceed, but cause Resolves to proceed without effect
        if action.parent_effect is not None and action.parent_effect.parent_card.cardclass == "Trap" and effect_state == STATE_RESOLVE:
            return True
        else:
            return False


class CantBeTargetedByTrap(Effect):
    def __init__(self):
        super().__init__("CBTbTrap", "CantBeTargeted")

    def init(self, gamestate, card):
        self.card = card
        self.is_negated = False

    def blocks_action(self, action, effect_state = STATE_NOTINEFFECT):
        if action.parent_effect.parent_card.cardclass == "Trap" and action.__class__.__name__ == "Target":
            return True
        else:
            return False


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


class ImperialIronWallTurnOnEffect(Effect):
    def __init__(self):
        super().__init__("ImperialIronWallTurnOn", "Trap")

    def init(self, gamestate, card):
        super().init(card)
        self.was_negated = False
        self.spellspeed = 2
        self.IIWpassiveeffect = ImperialIronWallPassiveEffect()
        self.IIWpassiveeffect.init(gamestate, card)

        self.IIWTO = Event("IIWTO", self.parent_card, self, "immediate", "", self.MatchIIWTurnOff)
        self.IIWTO.funclist.append(self.OnIIWTurnOff)

    def reqs(self, gamestate):
        return True

    def Activate(self, gamestate):
        pass

    def Resolve(self, gamestate):
        self.IIWpassiveeffect.TurnOn(gamestate)
        gamestate.immediate_events.append(self.IIWTO)
        
    def MatchIIWTurnOff(self, action):
        return action.__class__.__name__ == "TurnOffPassiveEffects" and action.zone.type == "Field" and action.card == self.parent_card

    def OnIIWTurnOff(self, gamestate):
        self.SWpassiveeffect.TurnOff(gamestate)
        if self.IIWTO in gamestate.immediate_events:
            gamestate.immediate_events.remove(self.IIWTO)


class ImperialIronWallPassiveEffect(PassiveEffect):
    def __init__(self):
        super().__init__("ImperialIronWallPassive", "Trap")

    def init(self, gamestate, card):
        super().init(card)
        self.is_on = False
        self.is_negated = False
        self.is_dormant = False

        self.intercepted_action = None

        self.BanishBan = engine.Bans.BanishBan()

        self.IIWOnCardBanished = Event("IIWOnBanish", self.parent_card, self, "immediate", "", self.MatchOnCardBanished)
        self.IIWOnCardBanished.funclist.append(self.PreventBanish)

    
    def MatchOnCardBanished(self, action):
        #I think the only way this would be possible is if the tozone was changed by another banishing effect
        matched = False
        if action.__class__.__name__ == "ApplyBansForChangeCardZone" and action.parentAction.name == CCZBANISH:
            self.intercepted_action = action.parentAction
            matched = True

        return matched

    def PreventBanish(self, gamestate):    
        self.intercepted_action.name = self.intercepted_action.intended_action
        self.intercepted_action.args['tozone'] = self.intercepted_action.intended_tozone

        #CCZ actions whose intended goal is to banish will all be caught by the ban, either at eventing time (check in the MatchEvent function),
        #before activation time (check in the reqs function) or at resolving time (in the Resolve function).

    def TurnOn(self, gamestate):
        if self.is_on == False and self.is_negated == False:
            self.is_on = True
            gamestate.add_ban(self.BanishBan)
            gamestate.immediate_events.append(self.IIWOnCardBanished)

    def TurnOff(self, gamestate):
        if self.is_on:
            gamestate.remove_ban(self.BanishBan)
            gamestate.immediate_events.remove(self.IIWOnCardBanished)

        self.is_on = False
        self.is_dormant = False

    

