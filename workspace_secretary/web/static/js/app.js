// Secretary Web UI - Alpine.js extensions and utilities

document.addEventListener('alpine:init', () => {
    // Email collapse animation
    Alpine.directive('collapse', (el, { expression }, { effect, cleanup }) => {
        const height = el.scrollHeight;
        
        effect(() => {
            if (el._x_isShown === false) {
                el.style.height = '0px';
                el.style.overflow = 'hidden';
            } else {
                el.style.height = height + 'px';
                el.style.overflow = 'visible';
            }
        });
    });
});

// HTMX configuration
document.body.addEventListener('htmx:configRequest', (event) => {
    // Add loading state
    document.body.classList.add('htmx-request');
});

document.body.addEventListener('htmx:afterRequest', (event) => {
    document.body.classList.remove('htmx-request');
});
