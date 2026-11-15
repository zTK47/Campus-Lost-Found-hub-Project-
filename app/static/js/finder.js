// Finder area: GET /items/{id}, GET /items/{id}/claims,
// PATCH /items/{id}/claims/{claim_id} (accept) and PATCH /items/{id} (return or reopen).
import { apiRequest } from "./api.js";
import {
  CLAIM_STATUS,
  clearMessage,
  el,
  formatDateTime,
  getParam,
  initPage,
  itemTag,
  showMessage,
  statusLabel,
} from "./common.js";

const referenceForm = document.getElementById("reference-form");
const message = document.getElementById("message");
const layout = document.getElementById("finder-layout");
const itemBox = document.getElementById("item");
const actionsBox = document.getElementById("item-actions");
const claimsList = document.getElementById("claims");
const claimsHint = document.getElementById("claims-hint");

let itemId = null;

function parseReference(value) {
  const number = Number(value);
  return Number.isInteger(number) && number >= 1 ? number : null;
}

async function loadItem({ keepMessage = false } = {}) {
  const [itemResponse, claimsResponse] = await Promise.all([
    apiRequest("GET", `/items/${itemId}`),
    apiRequest("GET", `/items/${itemId}/claims`),
  ]);

  if (itemResponse.status === 404) {
    layout.hidden = true;
    showMessage(message, "error", `There is no item with reference No. ${itemId}. Check the number in your confirmation.`);
    return;
  }
  if (!itemResponse.ok || !claimsResponse.ok) {
    layout.hidden = true;
    showMessage(message, "error", itemResponse.message || claimsResponse.message);
    return;
  }

  if (!keepMessage) clearMessage(message);
  layout.hidden = false;
  renderItem(itemResponse.data, claimsResponse.data);
  renderClaims(itemResponse.data, claimsResponse.data);
}

function renderItem(item, claims) {
  itemBox.replaceChildren(
    itemTag(item, { large: true, link: false }),
    el("p", { className: "claim-meta" }, el("a", { href: `/item?id=${item.id}`, text: "See the public page of this item" })),
  );

  if (item.status === "open") {
    actionsBox.replaceChildren(
      el("p", { text: "Accept the claim whose hidden detail matches the item. The other waiting claims are then rejected." }),
    );
    return;
  }

  if (item.status === "claimed") {
    const accepted = claims.find((claim) => claim.status === "accepted");
    const returnButton = el("button", { className: "button", type: "button", text: "Mark as returned" });
    const reopenButton = el("button", { className: "button button-quiet", type: "button", text: "Reopen item" });
    returnButton.addEventListener("click", () => changeItemStatus("returned", returnButton));
    reopenButton.addEventListener("click", () => changeItemStatus("open", reopenButton));

    actionsBox.replaceChildren(
      el("p", {
        text: accepted
          ? `You accepted the claim from ${accepted.claimant_name}. Arrange the handover by email, then mark the item as returned.`
          : "Arrange the handover, then mark the item as returned.",
      }),
      el("div", { className: "actions" }, [returnButton, reopenButton]),
      el("p", { className: "claim-meta", text: "Reopen the item if the handover did not happen. The accepted claim is then rejected and new claims are possible." }),
    );
    return;
  }

  actionsBox.replaceChildren(
    el("p", { text: "This item was returned. Its claims stay below as a record." }),
  );
}

function renderClaims(item, claims) {
  const waiting = claims.filter((claim) => claim.status === "pending").length;
  if (claims.length === 0) {
    claimsHint.textContent = "No claims yet. They appear here as soon as someone sends one.";
  } else if (item.status === "open" && waiting > 0) {
    claimsHint.textContent = waiting === 1 ? "1 claim is waiting for your review." : `${waiting} claims are waiting for your review.`;
  } else {
    claimsHint.textContent = "";
  }

  claimsList.replaceChildren(
    ...claims.map((claim) => {
      const canAccept = item.status === "open" && claim.status === "pending";
      const acceptButton = canAccept
        ? el("button", { className: "button", type: "button", text: "Accept this claim" })
        : null;
      if (acceptButton) {
        acceptButton.addEventListener("click", () => acceptClaim(claim, acceptButton));
      }

      return el("li", { className: "claim" }, [
        el("div", { className: "claim-head" }, [
          el("h3", { text: claim.claimant_name }),
          statusLabel(claim.status, CLAIM_STATUS),
        ]),
        el("p", {}, el("a", { href: `mailto:${claim.claimant_contact}`, text: claim.claimant_contact })),
        el("p", { className: "claim-meta", text: "Hidden detail" }),
        el("p", { className: "claim-proof", text: claim.proof_description }),
        el("p", { className: "claim-meta", text: `Claim No. ${claim.id}, sent ${formatDateTime(claim.created_at)}` }),
        acceptButton,
      ]);
    }),
  );
}

async function acceptClaim(claim, button) {
  button.disabled = true;
  const response = await apiRequest("PATCH", `/items/${itemId}/claims/${claim.id}`, { status: "accepted" });
  if (response.ok) {
    showMessage(message, "success", `Claim from ${claim.claimant_name} accepted. The item is now claimed and the other waiting claims were rejected.`);
  } else {
    showMessage(message, "error", response.message);
  }
  await loadItem({ keepMessage: true });
}

async function changeItemStatus(status, button) {
  if (status === "returned" && !window.confirm("Mark this item as returned? This cannot be undone.")) {
    return;
  }
  button.disabled = true;
  const response = await apiRequest("PATCH", `/items/${itemId}`, { status });
  if (response.ok) {
    const text = status === "returned"
      ? "Item marked as returned. It no longer appears in the default list of found items."
      : "Item reopened. The accepted claim was rejected and new claims are possible again.";
    showMessage(message, "success", text);
  } else {
    showMessage(message, "error", response.message);
  }
  await loadItem({ keepMessage: true });
}

referenceForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const reference = parseReference(referenceForm.elements.reference.value);
  if (reference === null) {
    layout.hidden = true;
    showMessage(message, "error", "Enter the reference number from your confirmation, for example 12.");
    referenceForm.elements.reference.focus();
    return;
  }
  itemId = reference;
  history.replaceState(null, "", `/finder?id=${itemId}`);
  loadItem();
});

initPage();
const fromUrl = parseReference(getParam("id"));
if (fromUrl !== null) {
  itemId = fromUrl;
  referenceForm.elements.reference.value = fromUrl;
  loadItem();
}
