function set_modal_give_revoke_access(){
    users_autocomplete("id_users");
    groups_autocomplete("id_groups");
    
    // The following is needed for select2 to work properly in a modal
    $('#id_users').select2({
	width: '100%',
	placeholder: 'Search for a user',
	minimumInputLength: 1,
	dropdownParent: $('#id-modal')
    });
    $('#id_groups').select2({
	width: '100%',
	placeholder: 'Search for a group',
	minimumInputLength: 1,
	dropdownParent: $('#id-modal')
    });
}
