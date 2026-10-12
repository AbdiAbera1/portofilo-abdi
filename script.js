const menuToggle = document.querySelector(".menu-toggle");
const navigationLinks = document.querySelector(".navigation-links");
const yearElement = document.querySelector("#current-year");
const contactForm = document.querySelector("#contact-form");
const formStatus = document.querySelector("#form-status");

if (menuToggle && navigationLinks) {
  menuToggle.addEventListener("click", () => {
    const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!isOpen));
    menuToggle.setAttribute("aria-label", isOpen ? "Open navigation menu" : "Close navigation menu");
    navigationLinks.classList.toggle("is-open", !isOpen);
  });

  navigationLinks.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Open navigation menu");
      navigationLinks.classList.remove("is-open");
    }
  });
}

if (yearElement) {
  yearElement.textContent = String(new Date().getFullYear());
}

if (contactForm instanceof HTMLFormElement) {
  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const submitButton = contactForm.querySelector('button[type="submit"]');
    if (!(submitButton instanceof HTMLButtonElement) || !(formStatus instanceof HTMLElement)) {
      console.error("The contact form is missing its submit button or status message.");
      return;
    }

    submitButton.disabled = true;
    formStatus.dataset.state = "";
    formStatus.textContent = "Sending your message…";

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(new FormData(contactForm))),
      });
      const result = await response.json();

      if (!response.ok) {
        formStatus.dataset.state = "error";
        formStatus.textContent = result.error || "Your message could not be sent. Please try again.";
        return;
      }

      contactForm.reset();
      formStatus.textContent = "Thanks for reaching out. Your message has been sent.";
    } catch (error) {
      console.error("Unable to submit the contact form.", error);
      formStatus.dataset.state = "error";
      formStatus.textContent = "We couldn’t connect to the message service. Please try again later.";
    } finally {
      submitButton.disabled = false;
    }
  });
}
