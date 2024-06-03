$(document).ready(function(){
    $(".sled_submit").click(function(e) {
	e.preventDefault();
	var dum = $(this).attr('href').split('page=');
	var page = dum[1].replace('#','');
	$('#id_page').val(page);
	$('#mysubmit').trigger('click');
    });
});
