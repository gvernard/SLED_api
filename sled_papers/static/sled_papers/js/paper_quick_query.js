function formatPaper(paper){
    if (paper.loading) {
	return paper.cite_as;
    }
    var $container = $(
	'<p><strong>' + paper.cite_as + '</strong><br><i>' + paper.title + '</i></p>'
    );    
    return $container;
}

function formatPaperSelection(paper){
    return paper.cite_as;
}


function set_modal_paper_quick_query(){
    $('#id_paper').select2({
	width: '100%',
	ajax: {
	    url: $("#Urlpapers").attr("data-url"),
	    dataType: 'json',
	    delay: 250,
	    data: function (params) {
		return {
		    q: params.term, // search term
		};
	    },
	    processResults: function (data, params) {
		var results = []
		$.each(data.papers,function(i,paper){
		    results.push({
			id: paper.id,
			cite_as: String(paper.cite_as),
			title: String(paper.title)
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
	placeholder: 'Search for a lead author or title',
	minimumInputLength: 1,
	dropdownParent: $('#id-modal'),
	templateResult: formatPaper,
	templateSelection: formatPaperSelection
    });

    $('#id_paper').on('select2:select', function (e) {
	$('#link').html(
	    '<a target="_blank" href="/sled_papers/detail/' + e.params.data.id + '">' + e.params.data.title + '</a>'
	);
    });

}
