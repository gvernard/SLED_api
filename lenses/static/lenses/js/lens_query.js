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
	// Check if queryset is empty
	var lenses_count = $('#lenses-count').val();
	if( lenses_count == 0 ){
	    alert('The query result is empty!');
	    return;
	}

	// Construct get query string
	var values = [];
	$('#exe_summary input[type="checkbox"]:checked').each(function() {
            values.push('ids=' + $(this).val());
	});
	
	if( values.length == 0 ){
	    alert('You must select at least one lens!');
	    return;
            //if( confirm('This will select the entire query result, i.e. '+lenses_count+' lenses!\nAre you sure you want to proceed?') ){
	    //	var get_str = '?' + $("#lens-query").serialize() + '&';
	    //}
	} else {
            var get_str = '?' + values.join('&') + '&';
	}
	
        var get_str = '?' + values.join('&') + '&';
	
        // Fetch only the first part of the URL (without any GET arguments)
        var url = $(this).data('form-url').split('?');
        var url_core = url[0];
        
        // Combine base URL with GET arguments and trigger modal
        var new_form_url = url_core + get_str;
        $(this).modalFormTrigger({
	    formURL: new_form_url,
	    modalID: "#id-modal"
        });
    });
   
    $('.data-form').find('input').change(function(){
	var id = $(this).parents('.data-form').attr('id');
	
	var exist = 0;
	$('#'+id).find('input').each(function(){
	    if( !$(this).attr('name').match('instrument_and') ){
		if( $(this).attr('type') == "checkbox" ){
		    if( $(this).is(":checked") ) {
			exist++;
		    }
		} else if( $(this).val().length != 0 ){
		    exist++;
		}
	    }
	});
	
	var target = $('#myTab button[data-target="#'+id+'"]');
	console.log(exist,target.html());
	if( exist == 0 ){
	    target.children('.badge').remove();
	} else {
	    if( target.children('.badge').length == 0 ){
		target.append('<span class="badge badge-pill badge-success"><img src="'+window.path_to_icon+'"></span>');
	    }
	}
    });
    
    
    set_help();    
});
