
import engine.GameState
import engine.Action as Action


class Effect:
    def __init__(self, name, etype, does_target):
        self.name = name
        self.type = etype
        self.does_target = does_target

class ImmuneToTrap(Effect):
    def __init__(self):
        super(ImmuneToTrap, self).__init__("ImmuneToTrap", "Immune", False)
    
    def init(self, gamestate, card):
        self.card = card
        self.is_negated = False

    def blockeffect(self, effect):
        if effect.etype == "Trap" and self.is_negated == False:
            return True
        else:
            return False

def BlockIfImmune_SingleTarget(target, effect):
    def decorator(func):
        def wrapper(*args, **kwargs):
            blocked = False
            if target.effect.etype == "Immune": 
                if target.effect.blockeffect(effect):
                    blocked = True
            if blocked == False:
                func(*args, **kwargs)
        return wrapper
    return decorator


#but what if a card cannot be targeted by an effect type?
class CantBeTargetedByTrap(Effect):
    def __init__(self):
        super(CantBeTargetedByTrap, self).__init__("CBTbTrap", "CantBeTargeted", False)

    def init(self, gamestate, card):
        self.card = card
        self.is_negated = False

    def blockeffect(self, effect):
        if effect.etype == "Trap" and effect.does_target == True and self.is_negated == False:
            return True
        else:
            return False

class BogusEffect(Effect):
    def __init__(self):
        super(BogusEffect, self).__init__("BogusEffect", "Trigger", False) 
        
    def init(self, gamestate, card): 
        
        self.card = card
        BETE = engine.Gamestate.TriggerEvent("BETE", self.MatchOnBMNormalSummon)
        BETE.funclist.append(self.ActivateOnTrigger)

        gamestate.triggerevents.append(BETE)  #le trigger effect activé par bogus effect est en if

    def MatchOnBMNormalSummon(self, action, gamestate):
        return action.name == "Normal Summon Monster" and action.card.ID == self.card.ID

    def ActivateOnTrigger(self, gamestate):
        print("running Bogus Effect On Summon Trigger")
        #create action of type ActivateMonster(OnTrigger)Effect with the desired sub-effect
        #then run this action
        #reqs will not be checked for the ActivateMonsterEffect action (BogusEffect is an if-trigger),
        #, but will be for the OnTriggerEffect

        theeffect = BogusOnTrigger()
        theeffect.init(self.card)

        theaction = Action.ActivateMonsterEffect()
        theaction.init(gamestate, self.card, theeffect)
        
        if theeffect.reqs(gamestate):
            theaction.run(gamestate)

class BogusOnTrigger(Effect):
    def __init__(self):
        super(BogusOnTrigger, self).__init__("BogusOnTrigger", "OnTrigger", True) 

    def init(self, card):
        self.BMcard = card
        self.was_negated = False
        self.spellspeed = 1

    def reqs(self, gamestate):
        targetplayer = self.BMcard.owner.other
        return len(targetplayer.deckzone.cards) > 0

    def Activate(self, gamestate):
        pass

    def Resolve(self, gamestate):
        targetplayer = self.BMcard.owner.other
        #send the top card of the opponent's deck to the graveyard : make an action for that
        pickedcard = targetplayer.deckzone.pop_card()
        targetplayer.graveyard.add_card(pickedcard)

        print(pickedcard.name + " sent to the graveyard")
        

class AlexDragonFictitiuousEffect(Effect):
    def __init__(self):
        super(AlexDragonFictitiuousEffect, self).__init__("AlexDragonEffect", "Ignition", False)
        
    def init(self, gamestate, card):
        self.ADcard = card
        self.was_negated = False
        self.spellspeed = 1

    def reqs(self, gamestate):
        return self.ADcard.location == "Field"

    def Activate(self, gamestate):
        self.ADcard.owner.add_life_points(gamestate, -100) #do an Action for that too 

    def Resolve(self, gamestate):
        #returns itself to the hand

        zonenum = self.ADcard.zone.zonenum
        self.ADcard.zonearray.pop_card(zonenum)
        self.ADcard.owner.hand.add_card(self.ADcard)

class TrapHoleEffect(Effect):
    def __init__(self):
        super(TrapHoleEffect, self).__init__("TrapHoleEffect", "Trap", True)
        
    def init(self, gamestate, card):
        self.THcard = card
        self.was_negated = False
        self.spellspeed = 2
        self.SummonedMonster = None

    def reqs(self, gamestate):
        lastactionscontainmatch = False
        for action in gamestate.lastresolvedactions:
            if action.name == "Normal Summon Monster" and action.card.face_up == True and action.card.attack >= 1000:
                blocked = False
                if action.card.effect.etype == "CantBeTargeted": 
                    if action.card.effect.blockeffect(self):
                        blocked = True
                
                if blocked == False:
                    #adjust the name criterion when there will be more summon types
                    #add a criterion checking if the card is untargetable by traps
                    print("Trap Hole : lastactions does contain a match")
                    lastactionscontainmatch = True
                    self.SummonedMonster = action.card
                    break
        """
        summonresponsewindowmatches = False
        if gamestate.insummonresponsewindow is not None:
            action = gamestate.insummonresponsewindow
            if action.card.face_up == True and action.card.attack >= 1000:
                summonresponsewindowmatches = True
                self.SummonedMonster = action.card
        """
        #Trap Hole actually works through the summon response window (but not the summon negation window) 
        #AND the summon response window will work through lastresolvedactions 
        
        return lastactionscontainmatch # or summonresponsewindowmatches 

    def Activate(self, gamestate):
        pass

    """
    @BlockIfImmune_SingleTarget(self.SummonedMonster, self)
    def Resolve(self, gamestate):
        DestroyAction = Action.DestroyCard()
        DestroyAction.init(self.SummonedMonster)
        DestroyAction.run(gamestate)

    """
    def Resolve(self, gamestate):
        blocked = False
        if self.SummonedMonster.effect.etype == "Immune":
            if self.SummonedMonster.effect.blockeffect(self):
                blocked = True
        if blocked == False:
            DestroyAction = Action.DestroyCard()
            DestroyAction.init(self.SummonedMonster)
            DestroyAction.run(gamestate)
    
#je pourrais essayer d'implementer ceci avec des decorateurs,
#exemple : un decorateur qui prendrait en argument le self.SummonedMonster et le self -- voir plus haut.
#mais on aurait alors des problemes avec les cartes qui touchent tous les monstres en meme temps,
#comme Dark Hole.

#le blocage des cartes qui sont CantBeTargeted dans le resolve aurait l'air de ceci :
#for zone in zonearray:
#   if zone.card.effect.etype == "CantBeTargeted" and zone.card.effect.blockeffect(self)   
#       numstoexclude.add zone.zonenum

#ca pourrait etre encapsule dans une fonction qui retourne un set de numstoexclude


class SmileWorldTurnOnEffect(Effect):
    def __init__(self):
        super(SmileWorldTurnOnEffect, self).__init__("SmileWorldTurnOnEffect", "Passive", False) 

    def init(self, gamestate, card):
        self.SWcard = card
        self.was_negated = False
        self.spellspeed = 1
        self.SWpassiveeffect = SmileWorldPassiveEffect()
        self.SWpassiveeffect.init(gamestate, card)
        
        self.SWTELF = engine.GameState.TriggerEvent("SWTELF", self.MatchOnSWLeavesField)
        self.SWTELF.funclist.append(self.OnSWLeavesField)

        gamestate.triggerevents.append(self.SWTELF)

    def reqs(self, gamestate):
        return True

    def Activate(self, gamestate):
        pass

    def Resolve(self, gamestate):
        self.SWpassiveeffect.TurnOn(gamestate)
        
    def MatchOnSWLeavesField(self, action):
        return action.name == "Card Leaves Field" and action.card.ID == self.SWcard.ID

    def OnSWLeavesField(self, gamestate):
        self.SWpassiveeffect.TurnOff(gamestate)


class SmileWorldPassiveEffect(Effect):
    def __init__(self):
        super(SmileWorldPassiveEffect, self).__init__("SmileWorldPassiveEffect", "Passive", False) 

    def init(self, gamestate, card):
        self.SWcard = card
        self.is_on = False
        self.is_negated = False
        self.is_dormant = False
        
        self.spellspeed = 1
        self.attack_increment = 0
        self.new_monster = None
        self.removed_monster = None

        self.SWTEOAM = engine.GameState.TriggerEvent("SWTEOAM", self.MatchOnMonsterEntersField)
        self.SWTEOAM.funclist.append(self.OnAddMonster)

        self.SWTEORM = engine.GameState.TriggerEvent("SWTEORM", self.MatchOnMonsterLeavesField)
        self.SWTEORM.funclist.append(self.OnRemoveMonster)

        

    def main_attack_increment_routine(self, amount, gamestate):
        turnplayermonsters = gamestate.turnplayer.monsterzones.occupiedzonenums
        otherplayermonsters = gamestate.otherplayer.monsterzones.occupiedzonenums

        for zonenum in turnplayermonsters:
            gamestate.turnplayer.monsterzones.get_card(zonenum).attack += amount
            print("Smile World : ",  gamestate.turnplayer.monsterzones.get_card(zonenum).name, " gained ", amount, " ATK")

        for zonenum in otherplayermonsters:
            gamestate.otherplayer.monsterzones.get_card(zonenum).attack += amount
            print("Smile World : ",  gamestate.otherplayer.monsterzones.get_card(zonenum).name, " gained ", amount, " ATK")


    def TurnOn(self, gamestate):
        if self.is_on == False and self.is_negated == False:
            self.is_on = True
            turnplayermonsters = gamestate.turnplayer.monsterzones.occupiedzonenums
            otherplayermonsters = gamestate.otherplayer.monsterzones.occupiedzonenums
            number_of_monsters_on_field = len(turnplayermonsters) + len(otherplayermonsters)
            self.attack_increment = number_of_monsters_on_field*100
                
            self.main_attack_increment_routine(self.attack_increment, gamestate)
                        
            gamestate.triggerevents.append(self.SWTEOAM)
            gamestate.triggerevents.append(self.SWTEORM)

        if self.is_negated:
            self.is_dormant = True  #i'm less sure about this part

    def MatchOnMonsterEntersField(self, action, gamestate):
        #should be "card enters field"
        #but I haven't created a class for this specific action yethttps://www.yomifrog.lima-city.de/xgm/en/Extended_Game_Mechanics_-_Chapter_6.php#p1
        if action.name == "Normal Summon Monster" and action.card.cardclass == "Monster":
            self.new_monster = action.card
            return True

        else:
            return False

    def MatchOnMonsterLeavesField(self, action, gamestate):
        
        #if action.name == "Card Leaves Field" and action.card.cardclass == "Monster":
        if action.name == "Card Leaves Field" and action.args['card'].cardclass == "Monster":
            self.removed_monster = action.card
            return True

        else:
            return False

    def OnAddMonster(self, gamestate):
        self.new_monster.attack += self.attack_increment
        
        self.main_attack_increment_routine(100, gamestate)

        self.attack_increment += 100

    def OnRemoveMonster(self, gamestate):
        self.removed_monster.attack -= self.attack_increment
        
        self.main_attack_increment_routine(-100, gamestate)

        self.attack_increment -= 100

    def TurnOff(self, gamestate):
        if self.is_on:
            
            self.main_attack_increment_routine(-1*self.attack_increment, gamestate)
            
            gamestate.triggerevents.remove(self.SWTEOAM)
            gamestate.triggerevents.remove(self.SWTEORM)
            

        self.is_on = False
        self.is_dormant = False

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
        

