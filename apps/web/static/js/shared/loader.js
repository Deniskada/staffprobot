(function () {
  const OVERLAY_ID = 'global-loader-overlay';
  const TEXT_ID = 'global-loader-text';

  function getOverlay() {
    return document.getElementById(OVERLAY_ID);
  }

  function getTextNode() {
    return document.getElementById(TEXT_ID);
  }

  function setBodyLocked(locked) {
    try {
      if (!document || !document.body) return;
      if (locked) {
        document.body.dataset._globalLoaderScroll = document.body.style.overflow || '';
        document.body.style.overflow = 'hidden';
      } else {
        const prev = document.body.dataset._globalLoaderScroll;
        if (prev !== undefined) {
          document.body.style.overflow = prev;
          delete document.body.dataset._globalLoaderScroll;
        } else {
          document.body.style.overflow = '';
        }
      }
    } catch (e) {
      // без фатальных ошибок
      console.warn('global-loader: failed to toggle body scroll', e);
    }
  }

  window.showGlobalLoader = function (message) {
    try {
      const overlay = getOverlay();
      if (!overlay) {
        console.warn('global-loader: overlay element not found');
        return;
      }
      const textNode = getTextNode();
      if (textNode) {
        textNode.textContent = message || 'Пожалуйста, подождите...';
      }
      overlay.classList.add('show');
      setBodyLocked(true);
    } catch (e) {
      console.warn('global-loader: show failed', e);
    }
  };

  window.hideGlobalLoader = function () {
    try {
      const overlay = getOverlay();
      if (!overlay) {
        return;
      }
      overlay.classList.remove('show');
      setBodyLocked(false);
    } catch (e) {
      console.warn('global-loader: hide failed', e);
    }
  };
})();
