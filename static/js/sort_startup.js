$(document).ready(
  function() {   
    $("table.table-striped").each(
	function(i,o) {
	    $(o).tablesorter();
	});
  });