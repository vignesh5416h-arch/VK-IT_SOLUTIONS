document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".nav-links");
  if (toggle && nav) {
    toggle.addEventListener("click", () => nav.classList.toggle("open"));
  }

  document.querySelectorAll(".alert").forEach((el) => {
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity .4s ease";
      setTimeout(() => el.remove(), 450);
    }, 4500);
  });

  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const password = form.querySelector('input[name="password"]');
      const confirm = form.querySelector('input[name="confirm_password"]');
      if (password && confirm && password.value !== confirm.value) {
        event.preventDefault();
        alert("Passwords do not match.");
      }
    });
  });
});
