$(document).ready(function() {

    // Modals
    $('#delete-group').modalForm({
	formURL: $('#delete-group').data("form-url"),
	modalID: "#id-modal",
	isDeleteForm: true
    });

    $(".sled-modal").each(function() {
	$(this).modalForm({
            formURL: $(this).data("form-url"),
            modalID: "#id-modal"
	});
    });

    $("#ask-to-join-group").modalForm({
	formURL: $("#ask-to-join-group").data("form-url"),
	modalID: "#id-modal"
    });
});
