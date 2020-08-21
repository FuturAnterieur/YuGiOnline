import engine.Effect as Effect
import engine.Action as Action

cardcounter = 0

FACEDOWN = 0
FACEUPTOCONTROLLER = 1
FACEUPTOEVERYONE = 2
FACEUPTOOPPONENT = 3

class Card:
    def __init__(self, name, text, cardclass, imgpath): 
        global cardcounter
        self.ID = cardcounter
        cardcounter += 1
        self.name = name
        self.face_up = FACEDOWN
        self.text = text
        self.cardclass = cardclass
        self.imgpath = imgpath

        self.owner = None
        self.location = ""
        self.zone = None
        self.zonearray = None
        self.actiondict = {}
        self.curchoices = set()

    def give_current_choices(self, gamestate):
        self.curchoices.clear()
        for action_name in self.actiondict.keys():
            if self.actiondict[action_name].reqs(gamestate):
                self.curchoices.add(action_name)

        return self.curchoices




class MonsterCard(Card):
    def __init__(self, name, attr, type, level, attack, defense, text, monsterclass, effect, imgpath):
        super(MonsterCard, self).__init__(name, text, 'Monster', imgpath)
        self.attribute = attr
        self.type = type
        self.level = level
        self.attack = attack
        self.originalattack = attack
        self.defense = defense
        self.originaldefense = defense
        self.monsterclass = monsterclass
        self.effect = effect
        
        self.numtributesrequired = 0
        self.position = "None"
        self.attacks_declared_this_turn = 0
        self.max_attacks_per_turn = 1
        self.summonmethod = "Normal"

        self.actiondict["Normal Summon"] = Action.NormalSummonMonster()
        self.actiondict["Attack"] = Action.DeclareAttack()
        
        if self.effect is not None:
            if self.effect.type == "Ignition":
                self.actiondict["Activate Effect"] = Action.ActivateMonsterEffect()

    def init_actions_and_effects(self, gamestate): #this function can be used at game initialization and when the card's controller changes.
        
        self.actiondict["Normal Summon"].init(self)
        self.actiondict["Attack"].init(self)

        if self.effect != None:
            self.effect.init(gamestate, self)
            if self.effect.type == "Ignition":
                self.actiondict["Activate Effect"].init(gamestate, self, self.effect)


class NormalMonsterCard(MonsterCard):
    def __init__(self, name, attr, type, level, attack, defense, text, imgpath):
        super(NormalMonsterCard, self).__init__(name, attr, type, level, attack, defense, text, "Normal", None, imgpath)
        if(self.level > 4 and self.level <= 6):
            self.numtributesrequired = 1
        elif(self.level > 6):
            self.numtributesrequired = 2


class SpellTrapCard(Card):
    def __init__(self, name, subclass, text, effect, imgpath):
        super(SpellTrapCard, self).__init__(name, text, "Spell/Trap", imgpath)
        self.wassetthisturn = False
        self.spelltrapsubclass = subclass
        self.effect = effect
        self.actiondict["Set"] = Action.SetSpellTrap()
        

    def init_actions_and_effects(self, gamestate):
        self.actiondict["Set"].init(self)

        self.effect.init(gamestate, self)

class TrapCard(SpellTrapCard):
    def __init__(self, name, text, effect, imgpath):
        super(TrapCard, self).__init__(name, "Normal Trap", text, effect, imgpath)
        self.actiondict["Activate"] = Action.ActivateNormalTrap()


    def init_actions_and_effects(self, gamestate):
        super(TrapCard, self).init_actions_and_effects(gamestate)
        self.actiondict["Activate"].init(self, self.effect)


class ContinuousSpellCard(SpellTrapCard):
    def __init__(self, name, text, effect, imgpath):
        super(ContinuousSpellCard, self).__init__(name, "Continuous Spell", text, effect, imgpath)
        if effect.type == "Passive":
            self.actiondict["Activate"] = Action.ActivateContinuousPassiveSpell()

    def init_actions_and_effects(self, gamestate):
        super(ContinuousSpellCard, self).init_actions_and_effects(gamestate)
        self.actiondict["Activate"].init(gamestate, self, self.effect)


