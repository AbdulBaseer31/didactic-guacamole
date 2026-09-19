(() => {
  if (window.__uixMut) return;
  let last = Date.now(), count = 0;
  const obs = new MutationObserver(m => { last = Date.now(); count += m.length; });
  const start = () => obs.observe(document.documentElement,
    {subtree: true, childList: true, attributes: true, characterData: true});
  if (document.documentElement) start();
  else document.addEventListener('DOMContentLoaded', start);
  window.__uixMut = { since: () => Date.now() - last, count: () => count };
})();