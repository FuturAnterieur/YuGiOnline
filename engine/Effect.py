
import engine.Action
from engine.Event import Event
import engine.Bans

from engine.Parameter import Parameter, UnaffectedModifier

from engine.defs import CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, CAUSE_EFFECT

class Effect:
    def __init__(self, name, etype, parent_card):
        self.parent_card = parent_card
        self.name = name
        self.type = etype
        self.is_negated = Parameter(self, 'is_negated', False)
        #other possibility:
        #self.params = {'is_negated' : Parameter(self, 'is_negated', False)}

        self.ActivateActionInfoList = []
        self.ResolveActionLInfoList = []

    
    def blocks_action(self, action, gamestate):
        return False

    def can_prevent_activation_attempt(self, in_activate_or_resolve):
        return False

    def affects_card(self, card, gamestate):
        affected = True
        for unaffected_function in card.unaffected.get_value(gamestate):
            if unaffected_function(self, gamestate):
                affected = False
                break

        return affected

    def check_if_activation_is_allowed(self, action_desc_list, gamestate):
        unbanned = True
        unblocked = True
        for action_desc in action_desc_list:
            for ban in gamestate.bans:
                if ban.bans_action(action_desc['action'], gamestate):
                    unbanned = False
                    break

            for effect in action_desc['card'].effects:
                if effect.blocks_action(action_desc['action'], gamestate) and effect.can_prevent_activation_attempt(action_desc['in_activate_or_resolve']):
                    unblocked = False
                    break

            if unbanned == False or unblocked == False:
                break

        return unbanned and unblocked


    def check_if_resolve_is_blocked(self, action_desc_list, gamestate):
        unbanned = True
        unblocked = True
        for action_desc in action_desc_list:
            for ban in gamestate.bans:
                if ban.bans_action(action_desc['action'], gamestate):
                    unbanned = False
                    break

            for effect in action_desc['card'].effects:
                if effect.blocks_action(action_desc['action'], gamestate):
                    unblocked = False
                    break

            if unbanned == False or unblocked == False:
                break

        return unbanned and unblocked


def MatchTurnSwitch(gamestate):
    return gamestate.curphase == "turn_switch"


class PassiveEffect(Effect):
    def __init__(self, name, etype, parent_card):
        super().__init__(name, etype, parent_card)
        self.is_on = False
        

def MatchOnADC(action, gamestate):
    return action.__class__.__name__ == "AfterDamageCalculationEvents"

class FlipEffect(Effect):
    def __init__(self, name, etype, parent_card):
        super(FlipEffect, self).__init__(name, etype, parent_card)
        self.ADC_event = None

    def RemoveADCEventFromTriggerEvents(self, gamestate):
        gamestate.trigger_events.remove(self.ADC_event)


#Todo : remake Unaffected and CantBeTargeted as card Parameters
#card effects apply modifiers to those parameters.

#in progress for Unaffected

class UnaffectedByTrap(Effect):
    def __init__(self, gamestate, card):
        super().__init__("ImmuneToTrap", "Immune", card)
        self.card = card
        UnaffectedByTrapModifier = UnaffectedModifier(self, None,  self.unaffected_by_trap, True)
        self.card.unaffected.local_modifiers.append(UnaffectedByTrapModifier)
        

    def unaffected_by_trap(self, effect, gamestate):
        unaffected = False
        if effect.parent_card.cardclass == "Spell/Trap" and effect.parent_card.spelltrapsubclass == "Trap":
            unaffected = True
    
        return unaffected
            


class CantBeTargetedByTrap(Effect):
    def __init__(self):
        super().__init__("CBTbTrap", "CantBeTargeted", card)

    def blocks_action(self, action, gamestate):
        is_negated = self.is_negated.get_value(gamestate)
        if action.parent_effect.parent_card.cardclass == "Trap" and action.__class__.__name__ == "Target" and is_negated == False:
            return True
        else:
            return False

    def can_prevent_activation_attempt(self, action_in_activate_or_resolve):
        return True


def getContinuousCardTurnOnEffectClass(name, passive_effect_class, spellspeed):
    class ContinuousCardTurnOnEffect(Effect):
        def __init__(self, gamestate, card):
            super().__init__(name, "Trap", card)
            self.PassiveEffectClass = passive_effect_class
            self.spellspeed = spellspeed

            self.passive_effect = self.PassiveEffectClass(name, "Passive", gamestate, card)
            
            self.TurnOffEvent = Event("PETO", self.parent_card, self, None, "immediate", "", self.MatchPETurnOff)
            self.TurnOffEvent.funclist.append(self.OnPETurnOff)

        def reqs(self, gamestate):
            return True

        def Activate(self, gamestate):
            pass

        def Resolve(self, gamestate):
            self.passive_effect.TurnOn(gamestate)
            gamestate.immediate_events.append(self.TurnOffEvent)
        
        def MatchPETurnOff(self, action, gamestate):
            return action.__class__.__name__ == "TurnOffPassiveEffects" and action.zone.type == "Field" and action.card == self.parent_card

        def OnPETurnOff(self, gamestate):
            self.passive_effect.TurnOff(gamestate)
            if self.TurnOffEvent in gamestate.immediate_events:
                gamestate.immediate_events.remove(self.TurnOffEvent)

    return ContinuousCardTurnOnEffect



class ImperialIronWallTurnOnEffect(Effect):
    def __init__(self):
        super().__init__("ImperialIronWallTurnOn", "Trap")

    def init(self, gamestate, card):
        super().init(card)
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
        self.spellspeed = 2

        self.intercepted_action = None

        self.BanishBan = engine.Bans.BanishBan(self)

    def TurnOn(self, gamestate):
        if self.is_on == False:
            self.is_on = True
            gamestate.add_ban(self.BanishBan) #negation check will go in the ban's function
            #gamestate.CCZBanModifiers.append(self.IIWOnCardBanished)

    def TurnOff(self, gamestate):
        if self.is_on:
            gamestate.remove_ban(self.BanishBan)
            #gamestate.CCZBanModifiers.remove(self.IIWOnCardBanished)

        self.is_on = False


