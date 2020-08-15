from django.db import models


# Create your models here.

class Duel(models.Model):

    duel_url = models.IntegerField(default=0)
    #can_begin = models.BooleanField(default=False)
    player_zero_joined = models.BooleanField(default=False)
    player_one_joined = models.BooleanField(default=False)

class Player(models.Model):

    duel = models.ForeignKey(Duel, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=25)
    player_number = models.IntegerField(default=0)
    sid = models.CharField(max_length=100, default="dpc")

class Spectator(models.Model):

    duel = models.ForeignKey(Duel, on_delete=models.CASCADE)
    

