
function Card(zoneId, coords, face_up, rotation, src, manager, ownerNo, id, indexInArray)
{
    this.zoneId = zoneId;
    
    this.x = coords.x;
    this.y = coords.y;
    this.angle = 0;
    
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
    this.height = this.manager.cardHeight;

    this.rotation = rotation; //"Vertical" or "Horizontal"

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
	if (this.angle != 0)
	{
		ctx.save();
		ctx.translate(this.x + this.width/2, this.y + this.height/2);
		ctx.rotate(this.angle*Math.PI / 180);
		ctx.translate(-1*(this.x + this.width/2), -1*(this.y + this.height/2));
	}
	ctx.drawImage(this.image_to_draw, this.x, this.y, this.width, this.height);

	if (this.angle != 0)
	{
		ctx.restore();
	}
    }
    this.undraw = function()
    {
	GameArea.context.clearRect(this.x, this.y, this.width, this.height);

    }
	
    

}


