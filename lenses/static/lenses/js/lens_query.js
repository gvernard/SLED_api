$(document).ready(function() {
    
    $('.sled_submit').click(function(event){
        event.preventDefault();
	var dum = $(this).attr('href').split('?');
	$('#lens-query').attr('action','?'+dum[1]);
	console.log($('#lens-query').attr('action'));
	$('#mysubmit').trigger('click');
    });
    
    
    $("#save-query").click(function() {
	// Check that the query form is not empty
	var myjson = $("#lens-query :input[name!=csrfmiddlewaretoken]").serialize() + '&'; // Need to end in & otherwise the last element remains
	var get_str = myjson.replace(/[^&]+=&/g, '').replace(/&[^&]+=$/g, '');
	
	if (get_str.length == 0) {
            alert('Query does not have any parameters!');
	} else {
            // Fetch only the first part of the URL (without any GET arguments)
            var url = $(this).data('form-url').split('?');
            var url_core = url[0];
	    
            // Trigger modal
            var new_form_url = url_core + '?' + get_str;
            $(this).modalFormTrigger({
		formURL: new_form_url,
		modalID: "#id-modal"
            });
	}
    });

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
    
});
