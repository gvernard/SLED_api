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
    
    // Scroll to opened pagination div
    var hash = window.location.hash
    if( hash ){
	$(hash).trigger("click");
	$('html,body').animate({scrollTop: $(hash).offset().top},'slow');
    }


    $(".slack-invite").click(function(e){
	e.preventDefault();
	$(this).modalFormTrigger({
	    formURL: $(this).data("form-url"),
	    modalID: "#id-modal",
	});
    });

    $('.same-page').click(function(e){
	e.preventDefault();
	var hash = $(this).attr('href');
	$(hash).trigger("click");
	$('html,body').animate({scrollTop: $(hash).offset().top},'slow');
    });
    
});
