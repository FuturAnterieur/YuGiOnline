
def AppendPlayerToEventCategory(trigger, gamestate):
    player_str = "TP" if trigger.card.owner == gamestate.turnplayer else "OP"

    return trigger.category + player_str

def GetEventCurrentPlayer(event, gamestate):
    return "TP" if event.card.owner == gamestate.turnplayer else "OP"

class Event:
    def __init__(self, name, card, effect, triggertype, category, matches):
        self.card = card
        self.type = triggertype #respond or trigger
        self.category = category
        self.name = name
        self.matches = matches
        self.funclist = []
        self.effect = effect
        self.in_timing = False

    def execute(self, gamestate):
        for func in self.funclist:
            func(gamestate)

    def is_spell_speed_sufficient(self, gamestate): 
        
        if gamestate.curspellspeed <= 1:
            return self.effect.spellspeed > gamestate.curspellspeed 

        elif gamestate.curspellspeed > 1:
            return self.effect.spellspeed >= gamestate.curspellspeed

    def is_in_timing_events(self, gamestate):
        #as things stand now, this will only be called in the case where the category is OFast,
        #but I provided functionality for the other categories

        #and anyway, it has been superseded by the in_timing flag
        full_category = ""
        if self.category == "OFast":
            full_category = self.type + "_" + self.category

        elif self.category in ['MSS1', 'OSS1']:
            full_category = self.type + "_" + self.category + GetEventCurrentPlayer(self, gamestate)

        if full_category != "":
            return self in gamestate.events_in_timing[full_category]

        else: #MFast : won't be used either
            return True
