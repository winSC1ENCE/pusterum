/**
 * Frontend JavaScript helpers for Atemtherapie Application
 */

document.addEventListener("DOMContentLoaded", () => {
    // Smooth scroll for anchor navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId && targetId !== '#') {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Log HTMX events in dev mode for debugging
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        document.body.addEventListener('htmx:responseError', function (evt) {
            console.error('HTMX Response Error:', evt.detail);
        });
    }
});
