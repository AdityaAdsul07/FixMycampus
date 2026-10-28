"use strict";

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const authMessage = document.getElementById("auth-message");

function showAuthMessage(text, isError = false) {
  authMessage.textContent = text;
  authMessage.className = "auth-message" + (isError ? " error" : "");
}

function showTab(which) {
  const login = which === "login";
  loginForm.hidden = !login;
  registerForm.hidden = login;
  tabLogin.classList.toggle("active", login);
  tabRegister.classList.toggle("active", !login);
  showAuthMessage("");
}

tabLogin.addEventListener("click", () => showTab("login"));
tabRegister.addEventListener("click", () => showTab("register"));

/* Only allow redirects to our own pages (no open redirect). */
function destinationAfterLogin(user) {
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && /^[a-z]+\.html$/.test(next)) {
    if (next !== "admin.html" || FMC.isStaff(user)) return next;
  }
  return FMC.isStaff(user) ? "admin.html" : "index.html";
}

async function submitAuth(form, path, body) {
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  showAuthMessage("Please wait...");

  try {
    const response = await fetch(`${FMC.API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      let detail = data.detail || `Request failed (${response.status})`;
      if (Array.isArray(detail)) {
        detail = detail.map(item => String(item.msg).replace(/^Value error, /, "")).join(" ");
      }
      throw new Error(detail);
    }

    FMC.saveAuth(data);
    window.location.href = destinationAfterLogin(data.user);
  } catch (error) {
    const offline = error instanceof TypeError;
    showAuthMessage(
      offline ? "Cannot reach the server. Is the backend running?" : error.message,
      true
    );
    button.disabled = false;
  }
}

loginForm.addEventListener("submit", event => {
  event.preventDefault();
  submitAuth(loginForm, "/auth/login", {
    email: document.getElementById("login-email").value,
    password: document.getElementById("login-password").value
  });
});

registerForm.addEventListener("submit", event => {
  event.preventDefault();

  const password = document.getElementById("register-password").value;
  if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    showAuthMessage("Password needs at least 8 characters, with a letter and a number.", true);
    return;
  }

  submitAuth(registerForm, "/auth/register", {
    full_name: document.getElementById("register-name").value,
    email: document.getElementById("register-email").value,
    password: document.getElementById("register-password").value
  });
});

/* Already logged in? Skip the form. */
const existing = FMC.getAuth();
if (existing) {
  window.location.replace(destinationAfterLogin(existing.user));
}
