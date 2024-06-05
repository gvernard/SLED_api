$(document).ready(function(){
    // Modals
    $(".sled-modal").each(function() {
        $(this).modalForm({
            formURL: $(this).data("form-url"),
            modalID: "#id-modal",
	    sled_onload: $(this).data("sled-onload"),
        });
    });
});
