$(document).ready(function() {
    function readURL(input, $img) {
	if (input.files && input.files[0]) {
            var reader = new FileReader();
            reader.onload = function(e) {
		$img.attr('src', e.target.result);
            }
            reader.readAsDataURL(input.files[0]);
	}
    }
    $(document).on("change", "input[name*='image']", function() {
	var $img = $(this).parent().parent().parent().find('img');
	readURL(this, $img);
    });

    set_help();
});
