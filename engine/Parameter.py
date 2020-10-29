#this will be used for attack/defense modification

#and maybe for managing effect negation too

class Parameter:
    def __init__(self, parent_object, name, base_value):
        self.parent_object = parent_object
        self.name = name
        self.base_value = base_value
        self.local_modifiers = []

    def apply_modifiers(self, gamestate):
        value = self.base_value
        for modifier in gamestate.modifiers:
            if modifier.matches(self, gamestate):
                value = modifier.function(self, value)

        for modifier in self.local_modifiers:
            #take modifier priority into account
            #no need for a matches test. Evaluate if the modifier 
            #is negated or if the target became unaffected to it 
            #for continuous modifiers only, and before it is put in the applicable_modifiers list.

            value = modifier.function(self, value)

        return value

    def get_value(self, gamestate):
        return self.apply_modifiers(gamestate)

    
class Modifier:
    def __init__(self, matches, function, modif_type, priority):
        self.matches = matches
        self.function = function
        self.type = modif_type
        self.priority = priority

    def check_for_unaffected_and_negated(self, gamestate):
        return True

class ContinuousModifier(Modifier):
    
    def check_for_negated(self, gamestate):
        return not self.parent_effect.is_negated.get_value(gamestate)

    def check_for_unaffected(self, gamestate):
        return self.parent_effect.check_if_subject_is_affected(self.targetcard, gamestate)

    def check_for_unaffected_and_negated(self, card, gamestate):
        return self.check_for_negated(gamestate) and self.check_for_unaffected(gamestate)

class LingeringModifier(Modifier):
    #this modifier's checks are ran at the time of trying to apply the effect (at resolution), in the effect's class,
    #and not afterwards. So in this class, all checks return True.
    pass
    

class CCZModifier(Modifier):
    def __init__(self, name, parent_card, parent_effect, scope_indicator, is_continuous, matches, function):
        self.name = name
        self.parent_card = parent_card
        self.parent_effect = parent_effect
        self.scope_indicator = scope_indicator
        self.matches = matches
        self.apply = function
        self.was_gained = False
        self.is_continuous = is_continuous

    def check_for_negated(self, gamestate):
        return not self.parent_effect.is_negated.get_value(gamestate)

    def check_for_unaffected(self, targetcard, gamestate):
        return self.parent_effect.check_if_subject_is_affected(targetcard, gamestate)
