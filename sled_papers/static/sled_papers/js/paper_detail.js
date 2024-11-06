$(document).ready(function() {
    var down_counter = 0;

    $("#export").click(function(){
	down_counter += 1;
	$(this).modalFormTrigger({
            formURL: $("#export").data("form-url"),
            modalID: "#id-modal"
	});
    });
    
    $('#delete-paper').click(function(e){
	if( down_counter > 0 ){
	    $(this).modalFormTrigger({
		formURL: $('#delete-paper').data("form-url"),
		modalID: "#id-modal",
		isDeleteForm: true
	    });
	} else {
	    alert('Make sure you export the paper data first before deleting!');
	}
    });    

    $("#lens-collage").click(function() {
	var url = $(this).data('form-url');
	document.location.href = url;
    });

});
