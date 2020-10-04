
import engine.Action
from engine.Event import Event
import engine.Bans

from engine.defs import CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, STATE_NOTINEFFECT, STATE_PRE_ACTIVATE, STATE_ACTIVATE, STATE_RESOLVE, CAUSE_EFFECT

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

    

