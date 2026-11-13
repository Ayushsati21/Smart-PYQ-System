// Compatibility entry point for the redesigned live application controller.
const redesignScript = document.createElement('script');
redesignScript.src = 'js/app-redesign.js';
document.currentScript.after(redesignScript);
