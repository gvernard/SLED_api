$(document).ready(function() {
    $('.p').hide();
    
    // Accordion
    $('input[type=checkbox]').click(function(){
	$(this).siblings('div').animate({
	    height: "toggle"
	}, 500, function() {
	    // Animation complete.
	});
    });

    // Modals
    $('.sled-delete-band,.sled-delete-instrument').each(function(){
	$(this).modalForm({
 	    formURL: $(this).data("form-url"),
 	    modalID: "#id-modal",
 	    isDeleteForm: true
	});
    });

    $(".sled-modal").each(function(){
	$(this).modalForm({
            formURL: $(this).data("form-url"),
 	    modalID: "#id-modal"
	});
    });


    // Scroll to opened accordion div
    if( hash ){
	$('#'+hash).trigger("click");
	//$('html,body').animate({scrollTop: $('#'+hash).offset().top},'slow');
    }
});
