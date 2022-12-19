$(document).ready(function() {
    $('.p').hide();

    $(".sled-process-lenses").click(function() {
	// Construct get query string
	var values = [];
	$('#exe_summary input[type="checkbox"]:checked').each(function() {
            values.push('ids=' + $(this).val());
	});

	if (values.length == 0) {
            alert('You need to select at least one item!');
	} else {
            var get_str = '?' + values.join('&') + '&';

            // Fetch only the first part of the URL (without any GET arguments)
            var url = $(this).data('form-url').split('?');
            var url_core = url[0];

            // Trigger modal
            var new_form_url = url_core + get_str;
            $(this).modalFormTrigger({
		formURL: new_form_url,
		modalID: "#id-modal"
            });
	}
    });

    // Modals
    $(".sled-modal").each(function() {
	$(this).modalForm({
            formURL: $(this).data("form-url"),
            modalID: "#id-modal"
	});
    });
    
    // Accordion
    $('input[type=checkbox]').click(function(){
	$(this).siblings('div').animate({
	    height: "toggle"
	}, 500, function() {
	    // Animation complete.
	});
    });

    // Scroll to open pagination div
    var hash = window.location.hash 
    if( hash ){
	$(hash).trigger("click");
	$('html,body').animate({scrollTop: $(hash).offset().top},'slow');
    }
});
