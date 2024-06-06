$(document).ready(function() {
    $('.js-captcha-refresh').click(function(){
	$form = $(this).parents('form');
	//$.getJSON($(this).data('url'), {}, function(json) {
        //    // This should update your captcha image src and captcha hidden input
	//});
	$.getJSON("/captcha/refresh/", function (result) {
            $('.captcha').attr('src', result['image_url']);
            $('#id_captcha_0').val(result['key'])
	});
	return false;
    });
});
