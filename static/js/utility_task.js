// Delete Task
$(document).on("click", ".delete-btn", function () {
  $(this).closest("tr").remove();
});

// Edit Task
$(document).on("click", ".edit-btn", function () {
  const row = $(this).closest("tr");
  const taskName = row.find("td:eq(1)").text();
  const taskCategory = row.find("td:eq(2)").text();

  // Prefill modal
  $("#taskName").val(taskName);
  $("#taskCategory").val(taskCategory);
  $("#taskModal").modal("show");

  // Save changes
  $("#taskForm")
    .off("submit")
    .on("submit", function (e) {
      e.preventDefault();
      row.find("td:eq(1)").text($("#taskName").val());
      row.find("td:eq(2)").text($("#taskCategory").val());
      $("#taskModal").modal("hide");
    });
});
