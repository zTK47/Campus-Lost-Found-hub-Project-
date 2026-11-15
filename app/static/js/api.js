// Small wrapper around fetch() for the Campus Lost & Found API.
// Every page uses it, so requests, responses and errors are handled the same way.

const ACTIVITY_KEY = "lost-found-api-activity";
const ACTIVITY_LIMIT = 10;

export async function apiRequest(method, path, body) {
  const options = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch {
    recordActivity(method, path, "no response");
    return {
      ok: false,
      status: 0,
      data: null,
      message: "The server cannot be reached. Check that it is running and try again.",
    };
  }

  let data = null;
  if (response.status !== 204) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }
  recordActivity(method, path, response.status);

  return {
    ok: response.ok,
    status: response.status,
    data,
    message: response.ok ? "" : errorMessage(response.status, data),
  };
}

// Turns an error response into one sentence for the page.
function errorMessage(status, data) {
  if (status === 422) {
    return "Some information is missing or not valid. Check the highlighted fields.";
  }
  if (data && typeof data.detail === "string") {
    return data.detail;
  }
  if (status >= 500) {
    return "The server had a problem. Try again in a moment.";
  }
  return `The request failed with status ${status}.`;
}

// Converts FastAPI 422 details into { fieldName: "message" }.
export function fieldErrors(data) {
  const errors = {};
  if (!data || !Array.isArray(data.detail)) {
    return errors;
  }
  for (const problem of data.detail) {
    const field = Array.isArray(problem.loc) ? problem.loc[problem.loc.length - 1] : "form";
    if (!errors[field]) {
      errors[field] = friendlyValidationMessage(problem);
    }
  }
  return errors;
}

function friendlyValidationMessage(problem) {
  const message = String(problem.msg || "");
  switch (problem.type) {
    case "missing":
      return "This field is required.";
    case "string_too_short":
      return "This field cannot be empty.";
    case "string_too_long":
      return `Use at most ${problem.ctx?.max_length ?? "the allowed number of"} characters.`;
    case "enum":
      return "Choose one of the options.";
    case "date_from_datetime_parsing":
    case "date_parsing":
    case "date_type":
      return "Enter a valid date.";
    case "value_error":
      if (message.includes("future")) return "The date cannot be in the future.";
      if (message.includes("email")) return "Enter a valid email address.";
      return message;
    default:
      return message || "This value is not valid.";
  }
}

// API activity: the last requests, shown in the footer to explain what the page does.
export function readActivity() {
  try {
    return JSON.parse(sessionStorage.getItem(ACTIVITY_KEY) || "[]");
  } catch {
    return [];
  }
}

function recordActivity(method, path, status) {
  const entry = { method, path, status, time: new Date().toLocaleTimeString("en-GB") };
  const entries = [entry, ...readActivity()].slice(0, ACTIVITY_LIMIT);
  try {
    sessionStorage.setItem(ACTIVITY_KEY, JSON.stringify(entries));
  } catch {
    // Storage can be unavailable (private mode); the activity list is optional.
  }
  document.dispatchEvent(new CustomEvent("api-activity"));
}
