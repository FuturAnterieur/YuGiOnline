
function Card(zoneId, face_up, src, manager, ownerNo, id, indexInArray)
{
    console.log('card constructor called.');
    this.zoneId = zoneId;
    var Coords = GetZoneCoords(zoneId);

    this.x = Coords.x;
    this.y = Coords.y;
    
    this.manager = manager;
    this.ownerNo = ownerNo;
    this.id = id;

    this.indexInArray = indexInArray;

    this.rectoLoaded = false;
    this.rectosrc = src;
    this.recto = new Image(); 
    this.recto.src = getImageFullPath(this.rectosrc);
    this.face_up = face_up;
    this.image_to_draw = face_up ? this.recto : this.manager.card_verso;

    this.scale = 1.0;
    this.width = this.manager.cardWidth;
    this.height = 88;

    this.rotation = "Vertical";

    this.right = this.x + this.width;
    this.bottom = this.y + this.height;
    this.top = this.y;

    this.mousewason = false;

    this.cardButtons = [];

    this.turn_face_down = function() 
    {
	this.face_up = false;
	this.image_to_draw = this.manager.card_verso;
    }

    this.turn_face_up = function ()
    {
	this.face_up = true;
	this.image_to_draw = this.recto;
    }


    this.draw = function()
    {
	ctx = GameArea.context;
	if (this.rotation == "Horizontal")
	{
		ctx.save();
		ctx.translate(this.x + this.width/2, this.y + this.height/2);
		ctx.rotate(90*Math.PI / 180);
		ctx.translate(-1*(this.x + this.width/2), -1*(this.y + this.height/2));
	}

	ctx.drawImage(this.image_to_draw, this.x, this.y, this.width, this.height);

	if (this.rotation == "Horizontal")
	{
	    ctx.restore();
	}
    }
    this.undraw = function()
    {
	GameArea.context.clearRect(this.x, this.y, this.width, this.height);

    }

}
