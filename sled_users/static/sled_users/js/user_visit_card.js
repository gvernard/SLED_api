$(document).ready(function(){
    $(".sled-modal").each(function() {
	$(this).modalForm({
            formURL: $(this).data("form-url"),
            modalID: "#id-modal"
	});
    });
});
