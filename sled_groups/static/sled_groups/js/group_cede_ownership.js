function set_modal_group_cede_ownership(){
    users_autocomplete('id_heir');
    $('#id_heir').select2({
	width: '100%',
	placeholder: 'Search for a user',
	minimumInputLength: 1,
	dropdownParent: $('#id-modal')
    });
}
