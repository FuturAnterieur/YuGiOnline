import engine.Zones as Zones
import math

class Player:
    def __init__(self, pid, gamestate):
        
        self.gamestate = gamestate

        self.monsters_on_field = []
        self.spelltraps_on_field = []

        self.player_id = pid
        strpid = str(pid)
        self.deckzone = self.register_zone(Zones.Deck(strpid + "_Deck", self))
        self.hand = self.register_zone(Zones.Hand(strpid + "_Hand",  self))
        self.monsterzones = self.register_zone_array(Zones.FieldZoneArray(strpid + "_Monster", self, 5, self.monsters_on_field))
        self.spelltrapzones = self.register_zone_array(Zones.FieldZoneArray(strpid + "_Spelltrap", self, 5, self.spelltraps_on_field)) 
        
        self.pendulumlowzone = self.spelltrapzones.listofzones[0]
        self.pendulumhighzone = self.spelltrapzones.listofzones[4]
        self.graveyard = self.register_zone(Zones.Graveyard(strpid + "_GY", self))
        self.banished = self.register_zone(Zones.Banished(strpid + "_Banished", self))
        self.fieldzone = self.register_zone(Zones.Zone(strpid + "_Field", 1, self, "FieldSpell"))
        self.lifepoints = 4000
        self.other = None
        self.normalsummonsperturn = 1
        self.gamestate = None

    def register_zone(self, zone):
        self.gamestate.zonesByName[zone.name] = zone
        return zone

    def register_zone_array(self, zoneArray):
        for zone in zoneArray.listofzones:
            self.gamestate.zonesByName[zone.name] = zone
        return zoneArray

    def add_card_to_deck(self, card):
        self.deckzone.add_card(card)

    def init_card_actions_and_effects(self, gamestate):
        for card in self.deckzone.cards:
            card.init_actions_and_effects(gamestate)

   
    def add_life_points(self, gamestate, amount):
        self.lifepoints += amount
        print("Player" + str(self.player_id) + "'s lifepoints are now at " + str(self.lifepoints))
        if(self.lifepoints <= 0):
            gamestate.end_condition_reached = True
            gamestate.add_player_to_winners(self.other)
        
