
function CoordsAreInsideObject(x,y, obj)
{
	var ret = true;
	if ((obj.bottom < y) || (obj.y > y) || (obj.right < x) || (obj.x > x)) 
	{
		ret = false;
        }
	return ret;
}

function Coords(x, y)
{
    this.x = x;
    this.y = y;

    this.substract = function(rhs)
    {
	return new Coords(this.x - rhs.x, this.y - rhs.y);
    }
}

function Zone(prefix, clientNo, name, x, y, width, height)
{
	this.localName = prefix + "_" + name;
	this.globalName = clientNo + "_" + name;

	this.x = x;
	this.y = y;
	this.width = width;
	this.height = height;
	this.bottom = this.y + this.height;
	this.right = this.x + this.width;
}
