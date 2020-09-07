
function CoordsAreInsideObject(x,y, obj)
{
	var ret = true;
	if ((obj.bottom < y) || (obj.y > y) || (obj.right < x) || (obj.x > x)) 
	{
		ret = false;
        }
	return ret;
}

function GetZoneCoords(zoneId)
{
	var targetLocation;
	var splitzone = zoneId.split("_");
	if (splitzone[0] == CardManager.perspectiveNo)
	{
	    targetLocation = ZoneCoords["my"][splitzone[1]];
	}
	else
	{
	    targetLocation = ZoneCoords["his"][splitzone[1]];
	}
	return targetLocation;
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
