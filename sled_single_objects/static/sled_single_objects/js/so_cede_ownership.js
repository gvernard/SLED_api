function set_modal_so_cede_ownership(){
    users_autocomplete('id_heir');
    
    // The following is needed for select2 to work properly in a modal
    $('#id_heir').select2({
	width: '100%',
	placeholder: 'Search for a user',
	minimumInputLength: 1,
	dropdownParent: $('#id-modal')
    });
}
