
function PhaseButton(phase_name, pna, x, y)
{
    this.x = x;
    this.y = y;

    this.width = 50;
    this.height = 35;

    this.bottom = this.y + this.height;
    this.right = this.x + this.width;

    this.isClicked = false;
    this.isClickable = false;
    
    this.isCurrentPhase = false;

    this.phase_name = phase_name;

    this.text = pna;

    this.draw = function ()
    {
	ctx = GameArea.context;

	if(this.isClicked == true)
	{
		ctx.fillStyle = "red";
	}
	else
	{
		ctx.fillStyle = "blue";
	}
	
	ctx.fillRect(this.x, this.y, this.width, this.height);
	
	ctx.font = "30px Consolas";
	ctx.fillStyle = "black";
	ctx.fillText(this.text, this.x, this.y + 27);
    }

    
    this.undraw = function ()
    {
	GameArea.context.clearRect(this.x, this.y, this.width, this.height);

    }
    
}
