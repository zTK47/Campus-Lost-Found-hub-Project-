// Report a found item: POST /items.
import { apiRequest, fieldErrors } from "./api.js";
import {
  CATEGORIES,
  clearFieldErrors,
  clearMessage,
  el,
  initPage,
  setFieldErrors,
  showMessage,
} from "./common.js";

const form = document.getElementById("report-form");
const message = document.getElementById("message");
const confirmation = document.getElementById("confirmation");

function today() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function prepareForm() {
  for (const [value, label] of Object.entries(CATEGORIES)) {
    form.elements.category.append(el("option", { value, text: label }));
  }
  form.elements.date_found.max = today();
}

function showConfirmation(item) {
  form.hidden = true;
  clearMessage(message);
  confirmation.hidden = false;
  confirmation.replaceChildren(
    el("div", { className: "message message-success flash", role: "status" }, [
      el("p", {}, el("strong", { text: `Item posted. Reference No. ${item.id}` })),
      el("p", { text: "Keep this number. You need it in the finder area to review claims for this item." }),
    ]),
    el("div", { className: "actions" }, [
      el("a", { className: "button", href: `/finder?id=${item.id}`, text: "Open the finder area" }),
      el("a", { className: "button button-quiet", href: `/item?id=${item.id}`, text: "See the public page" }),
      el("button", { className: "button button-quiet", type: "button", id: "report-another", text: "Report another item" }),
    ]),
  );
  document.getElementById("report-another").addEventListener("click", () => {
    form.reset();
    form.hidden = false;
    confirmation.hidden = true;
    form.elements.title.focus();
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFieldErrors(form);
  clearMessage(message);

  // Validation rules live in the API; the page shows its 422 errors next to the fields.
  const description = form.elements.description.value.trim();
  const item = {
    title: form.elements.title.value.trim(),
    category: form.elements.category.value,
    description: description || null,
    location_found: form.elements.location_found.value.trim(),
    date_found: form.elements.date_found.value,
    finder_contact: form.elements.finder_contact.value.trim(),
  };

  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  const response = await apiRequest("POST", "/items", item);
  button.disabled = false;

  if (response.status === 201) {
    showConfirmation(response.data);
    return;
  }
  showMessage(message, "error", response.message);
  if (response.status === 422) {
    setFieldErrors(form, fieldErrors(response.data));
  }
});

initPage();
prepareForm();
