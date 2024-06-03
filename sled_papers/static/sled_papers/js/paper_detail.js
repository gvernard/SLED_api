$(document).ready(function() {

    // Modals
    $('#delete-paper').modalForm({
	formURL: $('#delete-paper').data("form-url"),
	modalID: "#id-modal",
	isDeleteForm: true
    });

    $(".sled-modal").each(function() {
	$(this).modalForm({
            formURL: $(this).data("form-url"),
            modalID: "#id-modal"
	});
    });
    
});
