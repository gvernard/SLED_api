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
});
