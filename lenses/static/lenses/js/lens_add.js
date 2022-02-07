var counter = 0;

$( document ).ready(function() {
    // get the formset prefix first
    var prefix = $('#formset').attr('formset-prefix');
    counter = $('.sled-copy-target').length;
    
    $('.sled-copy-target').formset({
	added: reposition,
	removed: reset_counter,
	deleteContainerClass: "sled-delete-button",
	addContainerClass: "sled-add-button",
	prefix: prefix
    });

    $('.my-select2').each(function(index,element){
	$(element).attr('multiple','multiple');
	$(element).find('option')[0].remove();
    });
    $('.my-select2').select2({
	width: '180px',
	multiple: true,
	placeholder: 'Select an option'
    });
});

function reset_counter(row){
    $(".sled-lens-counter").each(function(index,element){
	//row.find('.my-select2').select2('destroy'); 
	$(element).text('Lens '+(index+1).toString());
	console.log((index+1).toString());
    });
    counter = $(".sled-lens-counter").length;
}

function reposition(form_div){
    form_div.detach().appendTo('#sled-lenses-table');
    form_div.find('.my-select2').each(function(index,element){
	$(element).attr('multiple','multiple');
	$(element).find('option')[0].remove();
    });
    $('.my-select2').select2({
	width: '180px',
	placeholder: 'Select an option'
    });
    counter = counter + 1;
    form_div.find('.sled-lens-counter').text('Lens '+counter.toString());
}
