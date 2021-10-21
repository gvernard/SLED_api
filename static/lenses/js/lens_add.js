$( document ).ready(function() {
    // The 'row' variable that is passed after the add event corresponds to .lens-form (which gets .dynamic-form now)
    $('.copy-target').formset({
	added: reposition,
	deleteContainerClass: "delete-button",
	addContainerClass: "add-button"
    });
    //move_remove($('.lens-form'));
    //move_add_another();
//     $('.delete-row').click(function() {
// 	alert( "Handler for .click() called." );
// 	$( this ).parents('.lens-form').parent().html('removed');
//     });
});


function reposition(form_div){
    form_div.detach().appendTo('.master');
}
