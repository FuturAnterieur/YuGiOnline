function CardButton(x, y, width, height, text, parentcard)
{
    this.text = text;
    this.parentcard = parentcard;

    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.bottom = this.y + this.height;
    this.right = this.x + this.width;

    this.isClicked = false;

    this.draw = function ()
    {
	ctx = GameArea.context;

	if (this.isClicked == false)
	{
		ctx.fillStyle = "blue";
	}
	else
	{
		ctx.fillStyle = "red";
	}
	ctx.fillRect(this.x, this.y, this.width, this.height);
	
	ctx.font = "30px Consolas";
	ctx.fillStyle = "black";
	ctx.fillText(this.text, this.x, this.y + this.height - 3);
    }

    this.undraw = function ()
    {
	GameArea.context.clearRect(this.x, this.y, this.width, this.height);

    }

}
