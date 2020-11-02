#this will be used for attack/defense modification

#and maybe for managing effect negation too

from engine.defs import UNAFFECTED

class CancellationNode:
    def __init__(self, modifier, affected_card):
        self.adjacents = []
        self.related_modifier = modifier
        self.affected_card = affected_card

    def is_active(self):
        return len([x for x in self.adjacents if x.is_active()]) == 0


class CancellationGraph:
    def __init__(self, start_modifier, start_card):
        self.nodes = []
        self.start_node = CancellationNode(start_modifier, start_card)
        self.nodes.append(start_node)


def find_adjacent_nodes(graph, node, previous_card, gamestate):
    modifier = node.related_modifier
    affected_card = node.affected_card
    if modifier.is_continuous:
        for negmod in modifier.parent_effect.is_negated.get_modifiers(gamestate):
            stop_check_at_unaffected = False
            if modifier.mod_type == UNAFFECTED:
                if modifier.unaff_func(negmod.parent_effect, gamestate):
                    stop_check_at_unaffected = True

            if not stop_check_at_unaffected and negmod.get_priority() > modifier.get_priority():
                newnode = CancellationNode(negmod, modifier.parent_effect.parent_card)
                graph.nodes.append(newnode)
                node.adjacents.append(newnode)
                find_adjacent_nodes(graph, newnode, modifier.parent_effect.parent_card, gamestate)

         
       
        for unaffmod in previous_card.unaffected.get_modifiers(gamestate):
            if unaffmod != modifier:
                unaffmod_unaffs_modifier = unaffmod.unaff_func(modifier.parent_effect, gamestate)
                condition = False
                if affected_card == previous_card and modifier.mod_type == UNAFFECTED:
                    modifier_unaffs_unaffmod = modifier.unaff_func(unaff_mod.parent_effect, gamestate)
                    if modifier_unaffs_unaffmod and unaffmod_unaffs_modifier: #conflict
                        condition = unaffmod.get_priority() >= modifier.get_priority()
                    elif not modifier_unaffs_unaffmod: #two unaffs on same card, but no conflict between them
                        condition = unaffmod_unaffs_modifier
                    else:
                        condition = False

                elif affected_card == previous_card and modifier.mod_type != UNAFFECTED:
                    condition = unaffmod_unaffs_modifier

                else: 
                    condition = False
                    #this is to prevent unaffected modifiers from causing a card to become
                    #negated by unaffected modifiers applying to other cards

                if condition:
                    newnode = CancellationNode(unaffmod, previous_card)
                    graph.nodes.append(newnode)
                    node.adjacents.append(newnode)
                    find_adjacent_nodes(graph, newnode, modifier.parent_effect.parent_card, gamestate)
                    

def build_cancellation_graph(start_modifier, start_card, gamestate):
    graph = CancellationGraph(start_modifier, start_card)
    find_adjacent_nodes(graph, graph.start_node, start_card, gamestate)
    return graph


class Parameter:
    def __init__(self, parent_object, name, base_value):
        self.parent_object = parent_object
        self.name = name
        self.base_value = base_value
        self.local_modifiers = []
        
        if name == 'is_negated':
            self.parent_card = parent_object.parent_card

        else:
            self.parent_card = parent_object

    def apply_modifiers(self, gamestate):
        
        value = self.base_value
        applicable_modifiers = []

        for modifier in gamestate.modifiers:
            if modifier.matches(self, gamestate):
                cancel_graph = build_cancellation_graph(modifier, self.parent_card)
                if cancel_graph.start_node.is_active():
                    applicable_modifiers.append(modifier)
                    
        for modifier in self.local_modifiers:           
            cancel_graph = build_cancellation_graph(modifier, self.parent_card)
            if cancel_graph.start_node.is_active():
                applicable_modifiers.append(modifier)

        for modifier in applicable_modifiers:
            value = modifier.function(self, value)

        return value


    def get_modifiers(self, gamestate):
        all_modifiers = []
        for modifier in gamestate.modifiers:
            if modifier.matches(self, gamestate):
                all_modifiers.append(modifier)

        all_modifiers.extend(self.local_modifiers)

        return all_modifiers

    def get_value(self, gamestate):
        return self.apply_modifiers(gamestate)


    

class Modifier:
    def __init__(self, parent_effect, matches, function, is_continuous, mtype):
        self.parent_effect = parent_effect
        self.matches = matches
        self.function = function
        self.is_continuous = is_continuous
        self.mod_type = mtype


class UnaffectedModifier(Modifier):
    def __init__(self, parent_effect, matches, function, unaff_func, is_continuous):
        super().__init__(parent_effect, matches, function, is_continuous, UNAFFECTED)
        self.unaff_func = unaff_func
        


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

    def is_not_negated(self, gamestate):
        return not self.parent_effect.is_negated.get_value(gamestate)

    def affects_card(self, targetcard, gamestate):
        return self.parent_effect.affects_card(targetcard, gamestate)
