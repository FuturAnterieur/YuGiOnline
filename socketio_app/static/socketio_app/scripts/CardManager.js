
var ZoneCoords = {'my': {}, 'his': {} };
var CardManager = {
    start : function(socket, clientnumber, duelid) 
    {
	this.turnplayer = '0';
	this.clientNo = clientnumber;
	this.duelid = duelid;
        this.socket = socket;
        this.card_verso = new Image();
        this.card_verso.src =  getImageFullPath('back_cover.jpg');
	
        this.cards = [];
	this.cardsById = new Object();
	this.cardButtons = [];
	this.clickMode = 0;
	this.cachedClickMode = 0;
	this.clickedCardId = "";
	this.clickedCardButtonIndex = -1;

	this.clickableCardIds = [];    

	this.intervals = [];
	this.numIntervals = 0;

	this.cardWidth = 60;
	
	this.phaseButtons = [new PhaseButton('draw_phase', 'DP', 200, 285), 
				new PhaseButton('standby_phase', 'SP', 300, 285),
				new PhaseButton('main_phase_1', 'MP1', 400, 285),
				new PhaseButton('battle_phase', 'BP', 500, 285),
				new PhaseButton('main_phase_2', 'MP2', 600, 285),
				new PhaseButton('end_phase', 'EP', 700, 285)];
	this.clickedPhaseButtonIndex = -1;

	this.PhaseFunctions = new Object();    

	ZoneCoords["my"]["Deck"] = new Coords(750, 500);
	ZoneCoords["my"]["GY"] = new Coords(750, 420);
	ZoneCoords["my"]["Hand"] = new Coords(450, 500);
	ZoneCoords["my"]["Monster2"] = new Coords(350, 360);
	ZoneCoords["my"]["Spelltrap3"] = new Coords(450, 420);

	ZoneCoords["his"]["Deck"] = new Coords(150, 20);
	ZoneCoords["his"]["GY"] = new Coords(150, 180);
	ZoneCoords["his"]["Hand"] = new Coords(450, 20);
	ZoneCoords["his"]["Monster2"] = new Coords(550, 180);
	ZoneCoords["his"]["Spelltrap3"] = new Coords(450, 90);
	
	this.moveList = [];
	this.cardsInHands = {'my': [], 'his': []};

	this.PhaseFunctions['draw_phase'] = function()
	    {
		console.log('draw phase began');
		CardManager.clickMode = -1;
		CardManager.phaseButtons[0].isCurrentPhase = true;

	    };

	this.PhaseFunctions['standby_phase'] = function()
	{
		console.log('standby phase began');
		CardManager.phaseButtons[0].isCurrentPhase = false;
		CardManager.phaseButtons[1].isCurrentPhase = true;
	};

	this.PhaseFunctions['main_phase_1'] = function()
	{
		console.log('main phase 1 began');
		CardManager.clickMode = 0;
		CardManager.phaseButtons[1].isCurrentPhase = false;
		CardManager.phaseButtons[2].isCurrentPhase = true;
		if(CardManager.clientNo == CardManager.turnplayer)
		{
			CardManager.phaseButtons[3].isClickable = true;
			CardManager.phaseButtons[4].isClickable = true;
			CardManager.phaseButtons[5].isClickable = true;
		}
	};

	this.PhaseFunctions['battle_phase'] = function()
	{
		console.log('battle phase began');
		CardManager.clickMode = 0;
		CardManager.phaseButtons[2].isCurrentPhase = false;
		CardManager.phaseButtons[3].isCurrentPhase = true;
		if(CardManager.clientNo == CardManager.turnplayer)
		{
			CardManager.phaseButtons[3].isClickable = false;
			CardManager.phaseButtons[4].isClickable = true;
			CardManager.phaseButtons[5].isClickable = false;
		}
	
	};

	this.PhaseFunctions['main_phase_2'] = function()
	{
		console.log('main phase 2 began');
		CardManager.clickMode = 0;
		CardManager.phaseButtons[2].isCurrentPhase = false;
		CardManager.phaseButtons[3].isCurrentPhase = false;
		CardManager.phaseButtons[4].isCurrentPhase = true;
		if(CardManager.clientNo == CardManager.turnplayer)
		{
			CardManager.phaseButtons[3].isClickable = false;
			CardManager.phaseButtons[4].isClickable = false;
			CardManager.phaseButtons[5].isClickable = true;
		}
	};

	this.PhaseFunctions['end_phase'] = function()
	{
		console.log('end phase began');
		CardManager.clickMode = -1;
		CardManager.phaseButtons[2].isCurrentPhase = false;
		
		CardManager.phaseButtons[4].isCurrentPhase = false;
		CardManager.phaseButtons[5].isCurrentPhase = true;
		if(CardManager.clientNo == CardManager.turnplayer)
		{
			CardManager.phaseButtons[3].isClickable = false;
			CardManager.phaseButtons[4].isClickable = false;
			CardManager.phaseButtons[5].isClickable = false;
		}
	};
	this.PhaseFunctions['turn_switch'] = function()
	{
		if (CardManager.turnplayer == '0')
		{
		    CardManager.turnplayer = '1';
		}
		else
		{
		    CardManager.turnplayer = '0';
		}

	};

    },
    checkClickPhaseButton : function(x, y, clickOrUnclick)
    {
	if (clickOrUnclick == 0)
	{
	    this.clickedPhaseButtonIndex = -1;
	}
	var unclickedButtonIndex = -1;

	for(var i = 0; i < this.phaseButtons.length; i++)
	{
	    if (CoordsAreInsideObject(x,y, this.phaseButtons[i]))
	    {
		if (clickOrUnclick == 0)
		{
		    if (this.phaseButtons[i].isClickable == true)
		    {
		        console.log('phase button clicked');
		        this.clickedPhaseButtonIndex = i;
		        this.phaseButtons[i].isClicked = true;
		        this.phaseButtons[i].draw();
		        break;
		    }
		}
		else
		{
		    unclickedButtonIndex = i;
		    if(i == this.clickedPhaseButtonIndex)
		    {
			this.phaseButtons[i].isClicked = false;
			this.phaseButtons[i].draw();
			this.socket.emit("ask_phase_change", {pnum: this.clientNo, duelid: this.duelid, phase: this.phaseButtons[i].phase_name });
		    }
		    break;
		}
	    }
	}

    },
    idInClickableCardIds(id)
    {
	var res = false;
	for(var i = 0; i < this.clickableCardIds.length; i++)
	{
	     if (id == this.clickableCardIds[i])
	     {
		res = true;
	        break;
	     }		       
	}
        return res;
    },
    enterChooseTargetCardMode(zoneType, targetPlayerNo)
    {
	this.clickMode = 2;
	for (var i = 0; i < this.cards.length; i++)
	{
	     curZoneData = this.cards[i].zoneId.split("_");
	     curPlayerNo = curZoneData[0];
	     curZoneType = curZoneData[1];
	     if(curZoneType == zoneType && curPlayerNo == targetPlayerNo)
	     {
		this.clickableCardIds.push(this.cards[i].id);
	     }
	}
    },

    checkClickCard : function(x, y, clickOrUnclick)
    {
	//console.log("Running checkClickCard");
	if (clickOrUnclick == 0) //a click
	{
	    //console.log("clickedCardId set to null");
	    this.clickedCardId = "";
	}
	
	for(var i = 0; i < this.cards.length; i++)
	{
	    if (CoordsAreInsideObject(x,y, this.cards[i]))
	    {
		if (clickOrUnclick == 0)
		{
		    if (this.clickMode == 0)
		    {
			if (this.cards[i].ownerNo == this.clientNo) //turnplayer checking will be done by the server
			{
		             this.clickedCardId = this.cards[i].id;
		             break; //only one card can be clicked at a time
			}
		    }
		    else if (this.clickMode == 2)
		    {
			if  (this.idInClickableCardIds(this.cards[i].id) )
			{
			       this.clickedCardId = this.cards[i].id;
			       break;
			}       
		    }
	        }
		else
		{
		    if (this.cards[i].id == this.clickedCardId)
		    {
			if (this.clickMode == 0)
			{
				this.socket.emit("ask_for_action_choices", {pnum: this.clientNo, duelid: this.duelid, cardid: this.clickedCardId});
				this.clickedCardId = "";
				break;
			}
			else if (this.clickMode == 2)
			{
			    this.socket.emit("target_card_chosen", {pnum: this.clientNo, duelid: this.duelid, cardid: this.clickedCardId});
		            this.clickedCardId = "";
			    this.clickableCardIds.splice(0, this.clickableCardsIds.length);
			    this.clickMode = 0;
			    break;
			}
		    }
		}
	    }
	}
    },
    checkClickCardButton : function(x, y, clickOrUnclick)
    {
	console.log("Running checkClickCardButton");
	if (clickOrUnclick == 0)
	{
	    this.clickedCardButtonIndex = -1;
	}
	var unclickedButtonIndex = -1;
	
	for(var i = 0; i < this.cardButtons.length; i++)
	{
	    if (CoordsAreInsideObject(x, y, this.cardButtons[i]))
	    {
		if (clickOrUnclick == 0)
		{
		    this.clickedCardButtonIndex = i;
		    this.cardButtons[i].isClicked = true;
		    this.cardButtons[i].draw();
		    break; //only one card can be clicked at a time
	        }
		else
		{
	            unclickedButtonIndex = i;
		    if (i == this.clickedCardButtonIndex)
		    {
			this.socket.emit("ask_run_action", {pnum: this.clientNo, duelid: this.duelid, cardid: this.cardButtons[i].parentcard.id, action_name: this.cardButtons[i].text });
			this.deleteCardButtons();
		    }
		    break;
		}
	    }
	}
	if (clickOrUnclick == 0 && this.clickedCardButtonIndex == -1)
	{
	    this.deleteCardButtons();
	}
	else if (clickOrUnclick == 1 && unclickedButtonIndex != this.clickedCardButtonIndex && this.clickedCardButtonIndex != -1)
	{
	    this.cardButtons[this.clickedCardButtonIndex].isClicked = false;
	    this.cardButtons[this.clickedCardButtonIndex].draw();
	}
    },
    
    createCard : function(zoneId, face_up, imgsrc, ownerNo, id)
    {
	console.log(zoneId + ' ' + id);
	
	newcard = new Card(zoneId, face_up, imgsrc, CardManager, ownerNo, id, this.cards.length);
	this.cards.push(newcard);
	this.cardsById[id] = newcard;
	
	this.cardsById[id].recto.onload = function() 
	{
	    CardManager.cardsById[id].draw();
	}
    },

    changeCardVisibility : function(id, visibility)
    {
	this.cardsById[id].undraw();
	if (visibility == "1")
	{
	    this.cardsById[id].turn_face_up()
	}
	else
	{
	    this.cardsById[id].turn_face_down()
	}

	this.cardsById[id].draw();
    },
    
    eraseCard : function(id)
    {
	console.log('erase card called on ' + id);
	this.cardsById[id].undraw();
	indexInArray = this.cardsById[id].indexInArray; 
        this.cards.splice(indexInArray, 1); 
	for (var i = indexInArray; i < this.cards.length; i++)
	{
		this.cards[i].indexInArray = i;
	}

        delete this.cardsById[id];
    },
			       
    createCardButtons : function(cardId, actionlist)
    {
	var theCard = this.cardsById[cardId];
	
	if (actionlist.length > 0)
	{
	    this.clickMode = 1;
	    console.log("creating card buttons");
	    
	    var newtop = theCard.y - actionlist.length*30;
	
	    for(var i = 0; i < actionlist.length; i++)
	    {
	        this.cardButtons.push(new CardButton(theCard.x, newtop + i*30, CardManager.cardWidth, 30, actionlist[i], theCard));
	    }
	    
	    this.drawCardButtons();
	}
    },
    deleteCardButtons : function()
    {
	for(var i = 0; i < this.cardButtons.length; i++)
	{
	    this.cardButtons[i].undraw();
	}
	this.cardButtons.splice(0, this.cardButtons.length);
	this.clickMode = 0;
    },
    moveCard : function(cardId, zoneId)
    {
	this.moveList.splice(0, this.moveList.length);
	this.numberOfCompletedMoves = 0;

	var theCard = this.cardsById[cardId];
	if (theCard.zoneId == zoneId)
	{
	     this.socket.emit('move_complete', {pnum: this.clientNo, duelid: this.duelid});
	}
	else
	{
	     var mainTargetLocation = GetZoneCoords(zoneId);
	     this.cachedClickMode = this.clickMode;
	     this.clickMode = -1;
	     var whichHand;
	     if (theCard.zoneId == "0_Hand" || theCard.zoneId == "1_Hand") //this part of the code could be called "program migration from hand"
	     {
	     	
		var splitzone = theCard.zoneId.split("_");
		var otherId;

		if (splitzone[0] == this.clientNo)
		{
			whichHand = 'my';
		}
		else
		{
			whichHand = 'his';
		}
		
		var spliced_position = theCard.indexInHand;	       
		this.cardsInHands[whichHand].splice(theCard.indexInHand, 1);
		theCard.indexInHand = undefined;
		var newNumCardsInHand = this.cardsInHands[whichHand].length;

		if (zoneId == "0_Hand" || zoneId == "1_Hand") //i.e. if the card is moving from one hand to the other
		{
			programMigrationToHand(theCard, zoneId);
		}
		else
		{
			this.moveList.push({card: theCard, tl: mainTargetLocation, completed: false});
		}

		for(var i = 0; i < spliced_position; i++)
		{
			this.moveList.push({card: this.cardsInHands[whichHand][spliced_position - i], 
			       		tl: this.getCardInHandPos(whichHand, newNumCardsInHand, spliced_position - i)});
		}

		for(var j = spliced_position; j < newNumCardsInHand; j++)
		{
			       this.moveList.push({card: this.cardsInHands[whichHand][j],
			       				tl: this.getCardInHandPos(whichHand, newNumCardsInHand, j)});

		}


 	     }

	     else if (zoneId == "0_Hand" || zoneId == "1_Hand")
	     {
		this.programMigrationToHand(theCard, zoneId);
		
		
	     }

	     else
	     {
		this.moveList.push({card: theCard, tl: mainTargetLocation});

             }

	     var numberOfMoves = this.moveList.length;	
	     for (var i = 0; i < numberOfMoves; i++)
	     {	
		card = this.moveList[i].card;
		tl = this.moveList[i].tl;
		this.cardDisplacement(card, tl, i);

	     }
	
	     theCard.zoneId = zoneId;
	}
    },

    programMigrationToHand : function(theCard, zoneId)
    {
	var splitzone = zoneId.split("_");
	var whichHand;
	if (splitzone[0] == this.clientNo)
	{
		whichHand = 'my';
	}
	else
	{
		whichHand = 'his';
	}	
	
	this.cardsInHands[whichHand].push(theCard);
	var newNumCardsInHand =  this.cardsInHands[whichHand].length;
	theCard.indexInHand = newNumCardsInHand - 1;

	for(var i = 0; i < newNumCardsInHand; i++)
	{
		this.moveList.push({card: this.cardsInHands[whichHand][i], tl: this.getCardInHandPos(whichHand, newNumCardsInHand, i)}) 	
			
	}


    },

    getCardInHandPos : function(whichHand, newNumCardsInHand, index)
    {
	var handCenter = ZoneCoords[whichHand]["Hand"];
	var centerIndex;
	var centerCardXPos;

	if (newNumCardsInHand % 2 == 1)
	{
	    centerIndex = Math.floor(newNumCardsInHand / 2);
	    centerCardXPos = handCenter.x - CardManager.cardWidth/2;
	}
	else
	{
	    centerIndex = newNumCardsInHand / 2;
	    centerCardXPos = handCenter.x;
	}

	var indexDelta = index - centerIndex;
	var sign = whichHand == "my" ? 1 : -1;
	var cardXPos = centerCardXPos + (indexDelta * sign * (CardManager.cardWidth + 5));

	return new Coords(cardXPos, handCenter.y);
    },

    cardDisplacement : function(theCard, targetLocation, displacementIndex)
    {
	var delta = new Coords(targetLocation.x - theCard.x, targetLocation.y - theCard.y);
	     var norme = Math.sqrt(delta.x*delta.x + delta.y*delta.y);
	     var speed = new Coords((delta.x/norme)*3, (delta.y/norme)*3); //constant speed version
	     //var speed = new Coords(delta.x/30, delta.y/30); //constant time version
	     
	     var intspeed = new Coords(Math.round(speed.x), Math.round(speed.y));
	     intspeed.x = speed.x > 0 ? Math.max(speed.x, 1) : Math.min(speed.x, -1);
	     intspeed.y = speed.y > 0 ? Math.max(speed.y, 1) : Math.min(speed.y, -1);
	     
 	     //add case where speed is 0 if delta is 0? Not absolutely necessary given the condition checks below.

	     absxspeed = Math.abs(intspeed.x);
	     absyspeed = Math.abs(intspeed.y);

	     
	     this.intervals[displacementIndex] = setInterval(function()
	     {

		xdiff = targetLocation.x - theCard.x;
		ydiff = targetLocation.y - theCard.y;
		absxdiff = Math.abs(xdiff);
		absydiff = Math.abs(ydiff);
		if (absxdiff > absxspeed || absydiff > absyspeed)
		{
		    GameArea.clear(); //leaves no marks, but forces to redraw the whole scene
		    //theCard.undraw(); //always ends up leaving marks one way or another
		    if (absxdiff > absxspeed)
		    {   
			theCard.x += intspeed.x;
			        
		    }
		    if (absydiff > absyspeed)
		    {
			theCard.y += intspeed.y;
		    }
			
		    CardManager.drawCards();
		    CardManager.drawPhaseButtons();
		}
		else
		{
		    if(absxdiff > 0 || absydiff > 0)
		    {
			theCard.undraw();
			theCard.x = targetLocation.x;
			theCard.y = targetLocation.y;
			theCard.draw();
		    }
		    theCard.bottom = theCard.y + theCard.height;
		    theCard.right = theCard.x + theCard.width;
	
		    clearInterval(CardManager.intervals[displacementIndex]);
		    CardManager.numberOfCompletedMoves += 1;
			
		    if (CardManager.moveList.length == CardManager.numberOfCompletedMoves)
	  	    {
		    	CardManager.clickMode = CardManager.cachedClickMode;
		    	CardManager.socket.emit('move_complete', {duelid: CardManager.duelid});
		    }
				
		}
	     }, 20);
    },

    rotateCard : function(cardid, rotation)
    {
	var theCard = this.cardsById[cardid];
	var degrees_counter = 0;
	if(theCard.rotation == rotation)
	{
		this.socket.emit('move_complete', {duelid: this.duelid});
	}
	else if (rotation == "Horizontal")
	{	
		ctx = GameArea.context;
		ctx.save();

		this.rotation_interval = setInterval(function() {
			


			theCard.undraw();
			ctx.translate(theCard.x + theCard.width/2, theCard.y + theCard.height/2);
			ctx.rotate(5*Math.PI / 180);
			ctx.translate(-1*(theCard.x + theCard.width/2), -1*(theCard.y + theCard.height/2));
			theCard.draw();
			
			degrees_counter += 5;
			if (degrees_counter >= 90)
			{
				clearInterval(CardManager.rotation_interval);
				theCard.rotation = "Horizontal";
				ctx.restore();
				CardManager.socket.emit('move_complete', {duelid: CardManager.duelid});
			}

		}, 100);
	}

    },

    drawPhaseButtons : function()
    {
	for(var i = 0; i < this.phaseButtons.length; i++)
    	{
		this.phaseButtons[i].draw();
    	}
    },

    drawCardButtons : function()
    {
	for(var i = 0; i < this.cardButtons.length; i++)
    	{
		this.cardButtons[i].draw();
    	}
    },
		       
    drawCards : function()
    {
	for(var i = 0; i < this.cards.length; i++)
    	{
		this.cards[i].draw();
    	}
    },
    drawCardById : function(id)
    {
	this.cardsById[id].draw();

    },

    sendAnswer : function(question_code, chosen_button)
    {
	this.socket.emit('send_answer', {pnum: this.clientNo, duelid: this.duelid, question: question_code, answer: chosen_button });
	this.clickMode = this.cachedClickMode;


	$('#message').text("");
	$('#choice_buttons').html("");

    },
    passAction : function()
    {
	this.socket.emit('pass_action',  {pnum: this.clientNo, duelid: this.duelid});
	$('#message').text("");
	$('#choice_buttons').html("");

    }
}
