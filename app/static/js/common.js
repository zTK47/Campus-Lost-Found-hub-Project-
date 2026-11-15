// Shared helpers for all pages: labels, formatting, DOM building and messages.
import { readActivity } from "./api.js";

// Same values as CATEGORY_VALUES in app/config.py.
export const CATEGORIES = {
  bottle: "Bottle",
  keys: "Keys",
  clothing: "Clothing",
  electronics: "Electronics",
  id_card: "ID card",
  bag: "Bag",
  other: "Other",
};

export const ITEM_STATUS = {
  open: "Open",
  claimed: "Claimed",
  returned: "Returned",
};

export const CLAIM_STATUS = {
  pending: "Waiting for review",
  accepted: "Accepted",
  rejected: "Rejected",
};

// Builds an element. Text is always set with textContent, never as HTML,
// so user input from the API cannot inject markup into the page.
export function el(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === undefined || value === null || value === false) continue;
    if (name === "text") element.textContent = value;
    else if (name === "className") element.className = value;
    else element.setAttribute(name, value === true ? "" : value);
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}

export function formatDate(isoDate) {
  const date = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatDateTime(isoDateTime) {
  const date = new Date(isoDateTime);
  if (Number.isNaN(date.getTime())) return isoDateTime;
  return date.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function statusLabel(status, labels = ITEM_STATUS) {
  return el("span", { className: `status status-${status}`, text: labels[status] || status });
}

export function categoryLabel(category) {
  return CATEGORIES[category] || category;
}

// The found-item tag used in the list and on the detail pages.
export function itemTag(item, { large = false, link = true } = {}) {
  const title = link
    ? el("a", { href: `/item?id=${item.id}`, text: item.title })
    : item.title;
  const heading = el(large ? "h1" : "h3", { className: "tag-title" }, title);

  return el("article", { className: large ? "tag tag-large" : "tag" }, [
    el("p", { className: "tag-ref" }, [
      el("span", { className: "visually-hidden", text: "Reference number " }),
      `No. ${item.id}`,
    ]),
    heading,
    el("div", { className: "tag-details" }, [
      el("p", { text: categoryLabel(item.category) }),
      el("p", { text: `Found in ${item.location_found}` }),
      el("p", { text: `on ${formatDate(item.date_found)}` }),
    ]),
    large && item.description
      ? el("p", { className: "tag-description", text: item.description })
      : null,
    statusLabel(item.status),
  ]);
}

export function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// Shows a message box. kind: "info", "success" or "error".
export function showMessage(container, kind, paragraphs) {
  container.replaceChildren();
  container.className = kind === "info" ? "message" : `message message-${kind}`;
  for (const paragraph of [].concat(paragraphs)) {
    container.append(paragraph instanceof Node ? paragraph : el("p", { text: paragraph }));
  }
  container.setAttribute("role", kind === "error" ? "alert" : "status");
}

export function clearMessage(container) {
  container.replaceChildren();
  container.className = "message";
}

// Puts 422 messages under the matching form fields.
export function setFieldErrors(form, errors) {
  clearFieldErrors(form);
  let first = null;
  for (const [field, message] of Object.entries(errors)) {
    const input = form.elements.namedItem(field);
    if (!input) continue;
    const errorId = `${field}-error`;
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", errorId);
    input.closest(".field").append(el("span", { className: "field-error", id: errorId, text: message }));
    first = first || input;
  }
  if (first) first.focus();
}

export function clearFieldErrors(form) {
  form.querySelectorAll(".field-error").forEach((node) => node.remove());
  form.querySelectorAll("[aria-invalid]").forEach((input) => {
    input.removeAttribute("aria-invalid");
    input.removeAttribute("aria-describedby");
  });
}

// Marks the current page in the navigation and sets up the API activity list.
export function initPage() {
  const here = window.location.pathname;
  document.querySelectorAll(".site-nav a").forEach((link) => {
    if (link.getAttribute("href") === here) link.setAttribute("aria-current", "page");
  });

  const toggle = document.querySelector(".activity-toggle");
  const panel = document.querySelector(".activity");
  if (!toggle || !panel) return;

  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!open));
    toggle.textContent = open ? "Show API activity" : "Hide API activity";
    panel.hidden = open;
    if (!open) renderActivity(panel);
  });
  document.addEventListener("api-activity", () => {
    if (!panel.hidden) renderActivity(panel);
  });
}

function renderActivity(panel) {
  const entries = readActivity();
  if (entries.length === 0) {
    panel.replaceChildren(el("p", { text: "No requests yet on this visit." }));
    return;
  }
  const rows = entries.map((entry) =>
    el("tr", {}, [
      el("td", { text: entry.time }),
      el("td", { text: entry.method }),
      el("td", { text: entry.path }),
      el("td", { text: String(entry.status) }),
    ]),
  );
  panel.replaceChildren(
    el("table", {}, [
      el("caption", { className: "visually-hidden", text: "Latest requests to the API" }),
      el("thead", {}, el("tr", {}, ["Time", "Method", "Path", "Status"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, rows),
    ]),
  );
}
