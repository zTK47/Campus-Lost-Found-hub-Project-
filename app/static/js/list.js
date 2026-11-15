// Found items list: GET /items with keyword, category, location and status filters.
import { apiRequest } from "./api.js";
import { CATEGORIES, el, getParam, initPage, itemTag, showMessage, clearMessage } from "./common.js";

const PAGE_SIZE = 12;
const FILTERS = ["q", "category", "location", "status"];

const form = document.getElementById("search-form");
const results = document.getElementById("results");
const count = document.getElementById("result-count");
const message = document.getElementById("message");
const showMore = document.getElementById("show-more");

let offset = 0;

function fillCategories() {
  const select = form.elements.category;
  for (const [value, label] of Object.entries(CATEGORIES)) {
    select.append(el("option", { value, text: label }));
  }
}

function readFiltersFromUrl() {
  for (const name of FILTERS) {
    const value = getParam(name);
    if (value) form.elements[name].value = value;
  }
}

function currentQuery() {
  const params = new URLSearchParams();
  for (const name of FILTERS) {
    const value = form.elements[name].value.trim();
    if (value) params.set(name, value);
  }
  return params;
}

async function loadItems({ append = false } = {}) {
  const params = currentQuery();
  params.set("limit", PAGE_SIZE);
  params.set("offset", offset);

  showMore.disabled = true;
  const response = await apiRequest("GET", `/items?${params}`);
  showMore.disabled = false;

  if (!response.ok) {
    showMessage(message, "error", response.message);
    count.textContent = "";
    return;
  }
  clearMessage(message);

  const { items, count: total } = response.data;
  if (!append) results.replaceChildren();
  for (const item of items) {
    results.append(el("li", {}, itemTag(item)));
  }

  const shown = offset + items.length;
  count.textContent = total === 1 ? "1 item found" : `${total} items found`;
  showMore.hidden = shown >= total;

  if (total === 0) {
    results.replaceChildren(
      el("li", { className: "empty-state" }, [
        el("p", { text: "No items match your search. Try a shorter keyword or remove a filter." }),
        el("p", {}, [
          "Found something yourself? ",
          el("a", { href: "/report", text: "Report a found item" }),
          ".",
        ]),
      ]),
    );
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  offset = 0;
  const query = currentQuery().toString();
  history.replaceState(null, "", query ? `/?${query}` : "/");
  loadItems();
});

showMore.addEventListener("click", () => {
  offset += PAGE_SIZE;
  loadItems({ append: true });
});

initPage();
fillCategories();
readFiltersFromUrl();
loadItems();
