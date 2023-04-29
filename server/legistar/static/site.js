function changeSummarizationStyle(event) {
  // get the form element
  const form = document.getElementById("summarization-style-form");

  // get the data
  const formData = new FormData(form);

  // get the "filter" field from the form data
  const filter = formData.get("filter");

  // the URL we are currently is of the form:
  // /foo/bar/previous-filter/
  // so we want to replace the "previous-filter" part with the new filter
  const currentPathname = window.location.pathname;
  const newPathname = currentPathname.replace(/\/[^\/]*\/$/, `/${filter}/`);

  // go to it!
  window.location.pathname = newPathname;
}


function doNothing(event) {
  event.preventDefault();
  event.stopPropagation();
}


// When the document is ready, make sure the summarization style is selected
// correctly, and set up the event handler for when it changes. Use basic 
// javascript; no jQuery.
document.addEventListener("DOMContentLoaded", function () {
  // get the current filter from the URL. It will be the final path component
  // of the URL, so split the URL on "/" and get the last element
  const splits = window.location.pathname.split("/");
  let filter = splits[splits.length - 2];

  // make sure it is one of the valid filters, which are:
  // `educated-layperson`, `high-school`, and `catchy-clickbait`
  if (!["concise", "educated-layperson", "high-school", "catchy-clickbait"].includes(filter)) {
    // if it is not one of the valid filters, default to `educated-layperson`
    filter = "concise";
  }

  // get the form element
  const form = document.getElementById("summarization-style-form");

  // select the correct option under the "filter" select element
  form.elements["filter"].value = filter;

  // set up the event handler for when the form is submitted
  form.addEventListener("submit", doNothing);

  // set up the event handler for when the form is changed
  form.addEventListener("change", changeSummarizationStyle);
});

