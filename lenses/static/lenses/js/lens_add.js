var counter = 0;

$( document ).ready(function() {
    // get the formset prefix first
    var prefix = $('#formset').attr('formset-prefix');
    counter = $('.sled-copy-target').length;
    
    $('.sled-copy-target').formset({
	added: reposition,
	removed: reset_counter,
	deleteContainerClass: "sled-delete-button",
	addContainerClass: "sled-add-button-hidden",
	prefix: prefix
    });

    $delete = $(".delete-row")
    $delete.bindFirst('click',function(e,next){
	$(this).closest('.sled-row-content').slideUp(1000);
	setTimeout(next, 1000); // holds the other handlers for 1sec
    });

    $(document).on("change", "input[name*='mugshot']", function() {
	var $img = $(this).parent().parent().parent().find('img');
	readURL(this, $img);
    });
    
    $('.my-select2').select2();
    
    set_help();
    
      $("#sled-add-another").click(function(e) {
	  $(".add-row").trigger("click");
	  set_help();
      });
    
});


function readURL(input, $img) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
	    $img.attr('src', e.target.result);
        }
        reader.readAsDataURL(input.files[0]);
    }
}

function reset_counter(row){
    $(".sled-lens-counter").each(function(index,element){
	$(element).text('Lens '+(index+1).toString());
	console.log((index+1).toString());
    });
    counter = $(".sled-lens-counter").length;
}

function reposition(form_div){
    form_div.detach();
    form_div.children('td').children('div').hide();
    form_div.appendTo('#sled-lenses-table');

    $delete = form_div.find(".delete-row")
    $delete.bindFirst('click',function(e,next){
	$(this).closest('.sled-row-content').slideUp(1000);
	setTimeout(next, 1000); // holds the other handlers for 1sec
    });

    form_div.find('.my-select2').each(function(index,element){
	$(element).select2();
    });

    counter = counter + 1;
    form_div.find('.sled-lens-counter').text('Lens '+counter.toString());

    form_div.children('td').children('div').slideDown(1000);
}

$.fn.bindFirst = function(type, handler) {
    return this.each(function() {
        var elm = this;
        var evs = $._data(this).events;
        if ( type in evs ) {
            var handlers = evs[type].map(function(ev) {
                return ev.handler;
            });
            $(elm).unbind(type).on(type, function(e) {
                handler.call(elm, e, function() {
                    handlers.forEach(function(fn) {
                        fn.call(elm);
                    });
                });
            });
        }
    });
};
