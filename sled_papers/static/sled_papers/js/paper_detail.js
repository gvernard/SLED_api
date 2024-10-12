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

    $("#lens-collage").click(function() {
	var url = $(this).data('form-url');
	document.location.href = url;
    });
    
});
