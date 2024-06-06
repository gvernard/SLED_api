$(document).ready(function(){

    $("input[type='checkbox']").each(function() {
	if( $(this).attr('checked') ){
	    $(this).parents(".inspect-image").addClass('sled-duplicate-required');
	} else {
	    $(this).parents(".inspect-image").removeClass('sled-duplicate-required');
	}
    });
    
    $("input[type='checkbox']").change(function() {
        $(this).parents(".inspect-image").toggleClass('sled-duplicate-required');
    });

    $('#mysubmit').on( "click", function(e) {
	e.preventDefault();
	var val = $('input[name="response"]:checked').val();
	if( val == 'All' ){
	    let text = "Are you sure you wnat to accept ALL the images?";
	    if( confirm(text) == true ){
		document.forms[0].submit();
	    }
	} else {
	    document.forms[0].submit();
	}
    });
    
});
