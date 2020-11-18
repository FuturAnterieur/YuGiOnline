import engine.Effect as Effect
import engine.Action as Action
import engine.ActionsSpellTrap as ActionsSpellTrap
import engine.Parameter as Parameter

from engine.defs import FACEDOWN


class Card:
    def __init__(self, name, text, cardclass, imgpath, ID, owner, gamestate): 
        
        self.ID = ID
        self.name = name
        self.face_up = FACEDOWN
        self.text = text
        self.cardclass = cardclass
        self.imgpath = imgpath

        
        self.unaffected = Parameter.Parameter(self, 'Unaffected', [])

        self.owner = owner
        self.location = ""
        self.zone = None
        self.zonearray = None
        self.actiondict = {}
        self.curchoices = set()

        self.CCZModifiers = []

        self.parameters = [self.unaffected]

    def refresh_and_give_current_choices(self, gamestate):
        self.curchoices.clear()
        for action_name in self.actiondict.keys():
            if self.actiondict[action_name].reqs(gamestate):
                self.curchoices.add(action_name)

        return self.curchoices

    def give_current_choices(self):
        return self.curchoices


class MonsterCard(Card):
    def __init__(self, name, attr, mtype, level, attack, defense, text, monsterclass, effects_classes, imgpath, ID, owner, gamestate):
        super().__init__(name, text, 'Monster', imgpath, ID, owner, gamestate)
        self.attribute = attr
        self.type = mtype
        self.level = level
        self.attack = attack
        self.originalattack = attack
        self.defense = defense
        self.originaldefense = defense
        self.monsterclass = monsterclass
        self.effects_classes = []
        self.effects = []
        
        self.numtributesrequired = 0
        self.position = "None"
        self.attacks_declared_this_turn = 0
        self.changed_battle_position_this_turn = False
        self.was_summoned_this_turn = False
        self.max_attacks_per_turn = 1
        self.can_attack_directly = False
        self.summonmethod = "Normal"

        self.actiondict["Normal Summon"] = Action.NormalSummonMonster()
        self.actiondict["Attack"] = Action.DeclareAttack()
        self.actiondict["Change Position"] = Action.ChangeBattlePosition()
        self.actiondict["Flip Summon"] = Action.FlipSummonMonster()

        self.actiondict["Normal Summon"].init(self)
        self.actiondict["Attack"].init(self)
        self.actiondict["Change Position"].init(self)
        self.actiondict["Flip Summon"].init(self)
        
        for effect_class in self.effects_classes:
            self.effects.append(effect_class(gamestate, self))
            if self.effects[-1].type == "Ignition":
                self.actiondict["Activate Effect"] = Action.ActivateMonsterEffect()
                self.actiondict["Activate Effect"].init(gamestate, self, self.effects[-1])


class NormalMonsterCard(MonsterCard):
    def __init__(self, name, text, imgpath, attr, mtype, level, attack, defense, ID, owner, gamestate):
        super().__init__(name, attr, mtype, level, attack, defense, text, 'Normal', [], imgpath, ID, owner, gamestate)
        if(self.level > 4 and self.level <= 6):
            self.numtributesrequired = 1
        elif(self.level > 6):
            self.numtributesrequired = 2


class SpellTrapCard(Card):
    def __init__(self, name, subclass, text, effect_class, imgpath, ID, owner, gamestate):
        super().__init__(name, text, "Spell/Trap", imgpath, ID, owner, gamestate)
        self.wassetthisturn = False
        self.spelltrapsubclass = subclass
        self.effects = [effect_class(gamestate, self)]
        self.actiondict["Set"] = ActionsSpellTrap.SetSpellTrap()
        self.actiondict["Set"].init(self)
        
        
        
class TrapCard(SpellTrapCard):
    def __init__(self, name, traptype, text, effect_class, imgpath, ID, owner, gamestate):
        super().__init__(name, 'Trap', text, effect_class, imgpath, ID, owner, gamestate)
        self.traptype = traptype


class NormalTrapCard(TrapCard):
    def __init__(self, name, text, imgpath, effect_class, ID, owner, gamestate):
        super().__init__(name, 'Normal', text, effect_class, imgpath, ID, owner, gamestate)
        self.actiondict["Activate"] = ActionsSpellTrap.ActivateNormalTrap()
        self.actiondict["Activate"].init(self, self.effects[0])

class ContinuousTrapCard(TrapCard):
    def __init__(self, name, text, imgpath, effect_class, ID, owner, gamestate):
        super().__init__(name, "Continuous", text, effect_class, imgpath, ID, owner, gamestate)
        self.actiondict["Activate"] = ActionsSpellTrap.ActivateContinuousTrap()
        self.actiondict["Activate"].init(self, self.effects[0])

class SpellCard(SpellTrapCard):
    def __init__(self, name, spelltype, text, effect_class, imgpath, ID, owner, gamestate):
        super().__init__(name, 'Spell', text, effect_class, imgpath, ID, owner, gamestate)
        self.spelltype = spelltype

class QuickPlaySpellCard(SpellCard):
    def __init__(self, name, text, imgpath, effect_class, ID, owner, gamestate):
        super().__init__(name, 'Quick-Play', text, effect_class, imgpath, ID, owner, gamestate)
        self.actiondict["Activate"] = ActionsSpellTrap.ActivateNormalOrQuickPlaySpell()
        self.actiondict["Activate"].init(self, self.effects[0])


class ContinuousSpellCard(SpellTrapCard):
    def __init__(self, name, text, imgpath, effect_class, ID, owner, gamestate):
        super().__init__(name, 'Continuous', text, effect_class, imgpath, ID, owner, gamestate)
        if self.effects[0].type == "Passive":
            self.actiondict["Activate"] = ActionsSpellTrap.ActivateContinuousPassiveSpell()
            self.actiondict["Activate"].init(gamestate, self, self.effects[0])

