$(document).ready(function() { 
    $('.sled-dupl-yes-no').on('click', function() {
	if ($(this).is(':checked')) {
	    var target = $(this).parents('tr').prev();
            target.removeClass("sled-duplicate-required");
            if ($(this).val() == 'yes') {
		target.removeClass("sled-duplicate-no").addClass("sled-duplicate-yes");
            } else {
		target.removeClass("sled-duplicate-yes").addClass("sled-duplicate-no");
            }
	}
    })
});
