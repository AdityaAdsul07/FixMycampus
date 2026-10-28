"use strict";

/* =========================================
   FIXMYCAMPUS - SHARED CONFIG & AUTH HELPERS
   Loaded first on every page. Change the API address here only
   (or set window.FMC_API_BASE before this script loads).
========================================= */

const FMC = (() => {
  const API_BASE = window.FMC_API_BASE || "http://127.0.0.1:8000/api";
  const STORAGE_KEY = "fmc_auth";

  function getAuth() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      return saved && saved.token && saved.user ? saved : null;
    } catch {
      return null;
    }
  }

  function saveAuth(response) {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ token: response.access_token, user: response.user })
    );
  }

  function clearAuth() {
    localStorage.removeItem(STORAGE_KEY);
  }

  function authHeaders(extra = {}) {
    const auth = getAuth();
    return auth ? { ...extra, Authorization: `Bearer ${auth.token}` } : extra;
  }

  function isStaff(user) {
    return Boolean(user) && (user.role === "admin" || user.role === "staff");
  }

  function logout() {
    clearAuth();
    window.location.href = "login.html";
  }

  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
  }

  /* Fills the "Log in / Log out" link and shows the Dashboard link for staff. */
  function initNav() {
    const link = document.getElementById("auth-link");
    if (!link) return;

    const auth = getAuth();
    if (!auth) {
      link.textContent = "Log in";
      link.href = "login.html";
      return;
    }

    link.textContent = `Log out (${auth.user.full_name.split(" ")[0]})`;
    link.href = "#";
    link.addEventListener("click", event => {
      event.preventDefault();
      logout();
    });

    const dashboard = document.getElementById("dashboard-link");
    if (dashboard && isStaff(auth.user)) dashboard.hidden = false;
  }

  document.addEventListener("DOMContentLoaded", initNav);

  return { API_BASE, getAuth, saveAuth, clearAuth, authHeaders, isStaff, logout, escapeHTML };
})();
