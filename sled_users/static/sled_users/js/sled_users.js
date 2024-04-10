$(document).ready(function() {
    $('.p').hide();

    // Gather selected ids before submitting the ids-form
    $(".sled-process-ids").click(function() {
	// Construct get query string
	var values = [];
	$(this).parents('form').find('input[type="checkbox"]:checked').each(function() {
            values.push('ids=' + $(this).val());
	});

	if( values.length == 0 ){
	    // Double check that there is at least one item selected
            alert('You need to select at least one item!');
	} else {
	    var obj_type = $(this).parents('form').find('input[name="obj_type"]').val();
            var get_str = '?' + values.join('&') + '&obj_type=' + obj_type + '&';
	    
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

    // Check that at least one item is selected in the ids-form
    $(".ids-form").submit(function(e){
	var checked_boxes = $(this).find('input[type="checkbox"]:checked');
	if( checked_boxes.length == 0 ){
	    alert('You must select at least one lens!');
	    e.preventDefault();
	}	
    });

    // Toggle select all in the ids-form
    $('.sled-toggle-all').click(function(e){
	var checkboxes = $(this).parents('form').find('input[type="checkbox"]');
	var new_status = e.currentTarget.getAttribute('value');
	if( new_status == "select" ){
	    for(var i=0;i<checkboxes.length;i++){
		checkboxes[i].checked = true;
	    }
	    e.currentTarget.setAttribute('value', 'unselect');
	} else {
	    for(var i=0;i<checkboxes.length;i++){
		checkboxes[i].checked = false;
	    }
	    e.currentTarget.setAttribute('value', 'select');
	}
    });


    $('.sled-toggle-access').click(function(e){
	var value = e.currentTarget.getAttribute('value');
	console.log(value);
	var table = $(this).siblings('.items-list').children('tbody');
	if( value == "PUB" ){
	    table.find('td.access-level:contains(PUB)').parent('tr').animate({ opacity: 100 });
	    table.find('td.access-level:contains(PRI)').parent('tr').animate({ opacity: 0 });
	    e.currentTarget.setAttribute('value','PRI');
	    $(e.target).html('Show PRI');
	} else if( value == "PRI" ){
	    table.find('td.access-level:contains(PUB)').parent('tr').animate({ opacity: 0 });
	    table.find('td.access-level:contains(PRI)').parent('tr').animate({ opacity: 100 });
	    e.currentTarget.setAttribute('value','');
	    $(e.target).html('Show All');
	} else {
	    table.find('td.access-level').parent('tr').animate({ opacity: 100 });
	    e.currentTarget.setAttribute('value','PUB');
	    $(e.target).html('Show PUB');
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

    // Scroll to opened pagination div
    var hash = window.location.hash 
    if( hash ){
	$(hash).trigger("click");
	$('html,body').animate({scrollTop: $(hash).offset().top},'slow');
    }
});
