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
            if modifier.matches(self):
                value = modifier.function(self, value)

        for modifier in self.local_modifiers:
            #take modifier priority into account
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

    


