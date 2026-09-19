function draw() {
  clear();
  const container = document.createElement('div');
  container.id = '__uix_overlay';
  container.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none;';
  document.documentElement.appendChild(container);

  const elements = document.querySelectorAll('[data-uix]');
  for (const el of elements) {
    const uix = el.getAttribute('data-uix');
    const r = el.getBoundingClientRect();
    const box = document.createElement('div');
    box.style.cssText = `
      position:fixed;
      left:${r.x}px;top:${r.y}px;
      width:${r.width}px;height:${r.height}px;
      border:2px solid #e5007d;
      box-sizing:border-box;
    `;
    container.appendChild(box);

    const badge = document.createElement('div');
    badge.textContent = uix;
    badge.style.cssText = `
      position:fixed;
      left:${r.x}px;top:${Math.max(0, r.y - 18)}px;
      background:#e5007d;color:#fff;
      font:11px monospace;padding:0 4px;
      border-radius:2px;line-height:16px;
      white-space:nowrap;
    `;
    container.appendChild(badge);
  }
}

function clear() {
  const overlay = document.getElementById('__uix_overlay');
  if (overlay) overlay.remove();
}