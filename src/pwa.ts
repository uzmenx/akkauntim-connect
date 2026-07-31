import { registerSW } from 'virtual:pwa-register';

const updateSW = registerSW({
  onNeedRefresh() {
    console.log("New content available, updating...");
    if ('serviceWorker' in navigator) {
       navigator.serviceWorker.getRegistration().then(reg => {
          if (reg && reg.waiting) {
             reg.waiting.postMessage({ type: 'SKIP_WAITING' });
          }
       });
    }
    setTimeout(() => {
      window.location.reload();
    }, 500);
  },
  onOfflineReady() {
    console.log("App ready to work offline.");
  },
  onRegisterError(error) {
    console.error("SW registration error", error);
  }
});
