$(document).ready(function() {
    $("#sled-add-collection").modalForm({
	formURL: $("#sled-add-collection").data("form-url"),
	modalID: "#id-modal",
	sled_onload: $("#sled-add-collection").data("sled-onload"),
    });
});

