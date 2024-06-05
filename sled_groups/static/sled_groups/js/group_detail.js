$(document).ready(function() {

    // Modals
    $('#delete-group').modalForm({
	formURL: $('#delete-group').data("form-url"),
	modalID: "#id-modal",
	isDeleteForm: true,
	sled_onload: $('#delete-group').data("sled-onload"),
    });

    $(".sled-modal").each(function() {
	$(this).modalForm({
            formURL: $(this).data("form-url"),
            modalID: "#id-modal",
	    sled_onload: $(this).data("sled-onload"),
	});
    });

    $("#ask-to-join-group").modalForm({
	formURL: $("#ask-to-join-group").data("form-url"),
	modalID: "#id-modal",
	sled_onload: $("#ask-to-join-group").data("sled-onload"),
    });
});
