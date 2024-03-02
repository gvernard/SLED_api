function global_search_autocomplete(target_id){
    $("#"+target_id).select2({
	ajax: {
	    url: $('#'+target_id).data('url'),
	    dataType: 'json',
	    delay: 250,
	    data: function (params) {
		return {
		    q: params.term, // search term
		};
	    },
	    processResults: function (data, params) {
		var results = []
		$.each(data,function(i,item){
		    results.push({
			type: item.type,
			name: item.name,
			link: item.link,
			match: item.match
		    });
		});
		
		return {
		    results: results,
		    pagination: {
			more: false
		    }
		};
	    },
	    cache: true
	},
	placeholder: 'Search',
	minimumInputLength: 1,
	dropdownCssClass: 'sled-global-search-result',
	templateResult: formatItem,
    });
}

function formatItem(item){
    if( item.loading ){
	return item.text;
    }
    var $container = $(
	"<div class='select2-result-repository clearfix'>" +
	    "<div class='select2-result-item__meta'>" +
            "<div class='select2-result-item__name'>"+
	    '&#x2022; '+item.type+' <a href="'+item.link+'" target="_blank">'+item.name+'</a>: '+item.match+
	    "</div>" +
	    "</div>" +
	    "</div>"
    );
    return $container;
}
