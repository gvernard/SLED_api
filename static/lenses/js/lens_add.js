$( document ).ready(function() {
    // The 'row' variable that is passed after the add event corresponds to .lens-form (which gets .dynamic-form now)
    $('.copy-target').formset({
	added: reposition,
	deleteContainerClass: "delete-button",
	addContainerClass: "add-button"
    });

    $('.my-select2').select2({
	placeholder: 'Select an option',
	width: '180px'
    });
    //move_remove($('.lens-form'));
    //move_add_another();
});


function reposition(form_div){
    form_div.detach().appendTo('.master');
    form_div.find('.my-select2').select2({
	placeholder: 'Select an option',
	width: '180px'
    });
}
