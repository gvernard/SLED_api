const horizontalAccordions = $(".accordion.width");

horizontalAccordions.each((index, element) => {
    const accordion = $(element);
  const collapse = accordion.find(".collapse");
  const bodies = collapse.find("> *");
  accordion.height(accordion.height());  
  bodies.width(bodies.eq(0).width());
  collapse.not(".show").each((index, element) => {
    $(element).parent().find("[data-toggle='collapse']").addClass("collapsed");
  });
});