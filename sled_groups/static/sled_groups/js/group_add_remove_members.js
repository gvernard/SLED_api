function set_modal_add_remove_members(){
    users_autocomplete('id_users');
    $('#id_users').select2({
	width: '100%',
	placeholder: 'Search for a user',
	minimumInputLength: 1,
	dropdownParent: $('#id-modal')
    });
}
