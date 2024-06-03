$(document).ready(function() {
    $("#create-new-group").modalForm({
	formURL: $("#create-new-group").data("form-url"),
	modalID: "#id-modal"
    });
});

