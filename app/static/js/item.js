// Public item detail: GET /items/{id}, and the claim form: POST /items/{id}/claims.
import { apiRequest, fieldErrors } from "./api.js";
import {
  clearFieldErrors,
  clearMessage,
  el,
  getParam,
  initPage,
  itemTag,
  setFieldErrors,
  showMessage,
} from "./common.js";

const pageMessage = document.getElementById("page-message");
const layout = document.getElementById("item-layout");
const itemBox = document.getElementById("item");
const form = document.getElementById("claim-form");
const claimMessage = document.getElementById("claim-message");

const itemId = Number(getParam("id"));

function claimCountText(count) {
  if (count === 0) return "Nobody has claimed this item yet.";
  if (count === 1) return "1 person has claimed this item so far.";
  return `${count} people have claimed this item so far.`;
}

function closedText(status) {
  if (status === "claimed") {
    return "The finder has accepted a claim for this item, so new claims are closed.";
  }
  return "This item was returned to its owner.";
}

function render(item) {
  document.title = `${item.title} | Campus Lost & Found`;
  itemBox.replaceChildren(
    itemTag(item, { large: true, link: false }),
    el("p", { className: "claim-meta", text: claimCountText(item.claim_count) }),
  );

  if (item.status !== "open") {
    form.hidden = true;
    showMessage(claimMessage, "info", closedText(item.status));
  }
}

async function loadItem() {
  if (!Number.isInteger(itemId) || itemId < 1) {
    showMessage(pageMessage, "error", [
      "This link has no valid reference number.",
      el("p", {}, el("a", { href: "/", text: "Go to the found items" })),
    ]);
    return null;
  }

  const response = await apiRequest("GET", `/items/${itemId}`);
  if (response.status === 404) {
    showMessage(pageMessage, "error", [
      `There is no item with reference No. ${itemId}.`,
      el("p", {}, el("a", { href: "/", text: "Search the found items" })),
    ]);
    return null;
  }
  if (!response.ok) {
    showMessage(pageMessage, "error", response.message);
    return null;
  }

  clearMessage(pageMessage);
  layout.hidden = false;
  render(response.data);
  return response.data;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFieldErrors(form);
  clearMessage(claimMessage);

  const claim = {
    claimant_name: form.elements.claimant_name.value.trim(),
    claimant_contact: form.elements.claimant_contact.value.trim(),
    proof_description: form.elements.proof_description.value.trim(),
  };

  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  const response = await apiRequest("POST", `/items/${itemId}/claims`, claim);
  button.disabled = false;

  if (response.status === 201) {
    form.hidden = true;
    showMessage(claimMessage, "success", [
      `Claim sent. Your claim No. ${response.data.id} is waiting for the finder's review.`,
      `If the finder accepts it, you will be contacted at ${response.data.claimant_contact}.`,
    ]);
    claimMessage.classList.add("flash");
    await loadItem();
    return;
  }

  if (response.status === 422) {
    showMessage(claimMessage, "error", response.message);
    setFieldErrors(form, fieldErrors(response.data));
    return;
  }

  showMessage(claimMessage, "error", response.message);
  if (response.status === 409) {
    await loadItem();
  }
});

initPage();
loadItem();
