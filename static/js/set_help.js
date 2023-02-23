function set_help(){
    $(".sled-help-tooltip").each(function(){
	if( !$(this).hasClass('tooltipstered') ){
	    var content = $(this).parent().children('div').eq(1).html();
	    $(this).tooltipster({
		position: 'left',
		theme: 'tooltipster-shadow',
		interactive: true,
		contentAsHTML: true,
		content: content,
		trigger: 'hover'
	    });
	}
    });
}
