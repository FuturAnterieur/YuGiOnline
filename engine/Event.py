
class Event:
    def __init__(self, name, card, effect, triggertype, category, matches):
        self.card = card
        self.type = triggertype #respond or trigger
        self.category = category
        self.name = name
        self.matches = matches
        self.funclist = []

    def execute(self, gamestate):
        for func in self.funclist:
            func(gamestate)

    def can_be_chained_now(self, gamestate): 
        if gamestate.is_building_a_chain == False:
            return False
        
        if gamestate.curspellspeed <= 1:
            return self.effect.spellspeed > gamestate.curspellspeed 

        elif gamestate.curspellspeed > 1:
            return self.effect.spellspeed >= gamestate.curspellspeed
