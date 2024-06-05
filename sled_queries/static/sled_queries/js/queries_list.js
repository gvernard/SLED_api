$(document).ready(function() {
    // Modals
    $('.sled-delete-query').each(function(){
	$(this).modalForm({
 	    formURL: $(this).data("form-url"),
 	    modalID: "#id-modal",
 	    isDeleteForm: true
	});
    });
    
    $(".sled-modal").each(function(){
	$(this).modalForm({
            formURL: $(this).data("form-url"),
 	    modalID: "#id-modal"
	});
    });
    
    $(".sled-view-query").click(function(){
	window.location.href = $(this).data("form-url");
    });
});
