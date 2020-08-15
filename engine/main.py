from Player import Player 
import Cards
import GameState
import Effect

yugi = Player(0)
kaiba = Player(1)

medesc0 = "A mystical defensive elf 0"
addesc0 = "An attack dragon 0"
dmdesc = "The ultimate wizard in terms of attack and defense."
ssdesc = "Level 6 example monster"

medesc1 = "A mystical defensive elf 1"
addesc1 = "An attack dragon 1"

sedesc = "Target 1 monster your opponent controls; this turn, if you Tribute a monster, you must Tribute that monster, as if you controlled it. You cannot conduct your Battle Phase the turn you activate this card."

supplysquaddesc = "Once per turn, if a monster(s) you control is destroyed by battle or card effect: Draw 1 card."

trdesc = "Your opponent cannot declare an attack this turn"

mysticalelf0 = Cards.NormalMonsterCard("Mystical Elf", "Light", "Spellcaster", 4, 800, 2000, medesc0)
alexdragon0 = Cards.NormalMonsterCard("Alexandrite Dragon", "Light", "Dragon", 4, 2000, 100, addesc0)
summonedskull0 = Cards.NormalMonsterCard("Summoned Skull", "Dark", "Fiend", 6, 2500, 1200, ssdesc) 
darkmagician0 = Cards.NormalMonsterCard("Dark Magician", "Dark", "Spellcaster", 7, 2500, 2000, dmdesc)
bogusmonster0 = Cards.NormalMonsterCard("Dummy1", "Fire", "Pyro", 3, 1000, 1500, "Nothing special here")
bogusmonster1 = Cards.MonsterCard("Dummy2", "Fire", "Pyro", 3, 1200, 1500, "Nothing special here", "Effect", Effect.BogusEffect())
#soulexchange0 = Cards.SpellCard("Soul Exchange", sedesc, "Normal", Effects.SoulExchangeEffect())
#supplysquad1 = Cards.ContinuousStaticSpellCard("Supply Squad", supplysquaddesc, Effects.SupplySquadTurnOnEffect())
#threateningroar = Cards.TrapCard("Threatening Roar", trdesc, "Normal", Effects.ThreateningRoarEffect())

traphole0 = Cards.TrapCard("Trap Hole", "When a monster is summoned with 1000+ ATK send it to the grave", Effect.TrapHoleEffect())
smileworld0 = Cards.ContinuousSpellCard("Smile World", "+100  per monster attack to each monster", Effect.SmileWorldTurnOnEffect())

mysticalelf1 = Cards.NormalMonsterCard("Mystical Elf", "Light", "Spellcaster", 4, 800, 2000, medesc1)
alexdragon1 = Cards.MonsterCard("Alexandrite Dragon", "Light", "Dragon", 4, 2000, 100, addesc1, "Effect", Effect.AlexDragonFictitiuousEffect())

yugi.give_deck([darkmagician0, mysticalelf0, bogusmonster1, traphole0])
kaiba.give_deck([bogusmonster0, summonedskull0, alexdragon1, smileworld0])

#yugi.give_deck([darkmagician0, mysticalelf0, soulexchange0])
#kaiba.give_deck([mysticalelf1, summonedskull0,alexdragon0])

theduel = GameState.GameState(yugi, kaiba)

while(theduel.winner is None):
    theduel.progress()

print("Player" + str(theduel.winner.player_id) + " has won the duel.")
