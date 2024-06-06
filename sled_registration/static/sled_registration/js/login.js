$(document).ready(function() {
    $('form').each(function() {
	if (!$(this).is('[action]')) {
	    $(this).attr('action', '/');
	}
    });
    // $('#id_username').addClass('text-field',"w-input").attr({"data-name":'Name'});
});
