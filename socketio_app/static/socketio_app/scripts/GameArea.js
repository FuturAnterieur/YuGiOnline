
var GameArea = {
    canvas : document.createElement("canvas"),
    start : function() {

        this.canvas.width = 900;
        this.canvas.height = 600;
        this.context = this.canvas.getContext("2d");
        document.body.insertBefore(this.canvas, document.body.childNodes[0]);

	window.addEventListener('mousedown', function (e) {
		GameArea.clicking = true;
		GameArea.checkClickEvent(e.pageX, e.pageY, 0);

		//during card movement events, clickMode will be set to -1
	})
	window.addEventListener('mouseup', function (e) {
		GameArea.clicking = false;
		GameArea.checkClickEvent(e.pageX, e.pageY, 1);
	})
    },

    checkClickEvent : function(epageX, epageY, clickOrUnclick) {
		if (CardManager.clickMode == 0)
		{
		    CardManager.checkClickCard(epageX, epageY, clickOrUnclick);
		}
		else if (CardManager.clickMode == 1)
		{
		    CardManager.checkClickCardButton(epageX, epageY, clickOrUnclick);
		}
		else if (CardManager.clickMode == 2)
		{
		    CardManager.checkClickCard(epageX, epageY, clickOrUnclick);
		}
		else if (CardManager.clickMode == 3)
		{
		    CardManager.checkClickPhaseButton(epageX, epageY, clickOrUnclick);
		}

    },

    clear : function() {
	this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
}
