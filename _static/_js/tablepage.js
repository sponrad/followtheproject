$(document).ready( function () {
    var keys = new KeyTable();
    
    /* Apply a return key event to each cell in the table */
    keys.event.action( null, null, function (nCell) {
	/* Block KeyTable from performing any events while jEditable is in edit mode */
	keys.block = true;
	
	/* Initialise the Editable instance for this table */
	$(nCell).editable( function (sVal) {
	    /* Submit function (local only) - unblock KeyTable */
	    keys.block = false;
	    return sVal;
	}, { 
	    "onblur": 'submit', 
	    "onreset": function(){ 
		/* Unblock KeyTable, but only after this 'esc' key event has finished. Otherwise
		 * it will 'esc' KeyTable as well
		 */
		setTimeout( function () {keys.block = false;}, 0); 
	    }
	} );
	
	/* Dispatch click event to go into edit mode - Saf 4 needs a timeout... */
	setTimeout( function () { $(nCell).click(); }, 0 );
    } );

    $(".edit").editable("");

    $("a.removefilter").click(function(e) {
	e.preventDefault();
	//Ajax request to delete the filter
	$(this).parent().hide(0, function(){
	    $(this).remove();
	});
    });
} );
