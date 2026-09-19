(() => {
  const MAX = __MAX_ELEMENTS__;
  const SEL = 'a[href], button, input:not([type="hidden"]), select, textarea, ' +
              'summary, [role], [onclick], [tabindex]:not([tabindex="-1"]), ' +
              '[contenteditable="true"]';

  const isVisible = el => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') return false;
    if (parseFloat(s.opacity) < 0.05) return false;
    if (el.closest('[aria-hidden="true"]')) return false;
    return true;
  };

  const inViewport = el => {
    const r = el.getBoundingClientRect();
    return r.bottom > -50 && r.top < innerHeight + 50 &&
           r.right > -50 && r.left < innerWidth + 50;
  };

  const TAG_ROLE = {A:'link', BUTTON:'button', SELECT:'combobox',
                    TEXTAREA:'textbox', SUMMARY:'button'};

  const roleOf = el => {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit.split(/\s+/)[0];
    if (el.tagName === 'INPUT') {
      const t = (el.type || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'search') return 'searchbox';
      if (['submit','button','reset','image'].includes(t)) return 'button';
      return 'textbox';
    }
    return TAG_ROLE[el.tagName] || el.tagName.toLowerCase();
  };

  const labelledBy = el => {
    const ids = el.getAttribute('aria-labelledby');
    if (!ids) return null;
    return ids.split(/\s+/)
              .map(i => (document.getElementById(i) || {}).innerText || '')
              .join(' ');
  };

  const nameOf = el => {
    const isBtnInput = el.tagName === 'INPUT' &&
                       ['submit','button'].includes((el.type || '').toLowerCase());
    const cands = [
      el.getAttribute('aria-label'),
      labelledBy(el),
      (el.labels && el.labels[0]) ? el.labels[0].innerText : null,
      el.getAttribute('placeholder'),
      el.getAttribute('alt'),
      el.getAttribute('title'),
      isBtnInput ? el.value : null,
      el.innerText,
      el.getAttribute('name'),
    ];
    for (const c of cands) {
      if (c && c.trim()) return c.trim().replace(/\s+/g, ' ').slice(0, 120);
    }
    return '';
  };

  const cssPath = el => {
    const parts = [];
    let cur = el, depth = 0;
    while (cur && cur.nodeType === 1 && depth < 6) {
      let seg = cur.tagName.toLowerCase();
      const p = cur.parentElement;
      if (p) {
        const sibs = [...p.children].filter(c => c.tagName === cur.tagName);
        if (sibs.length > 1) seg += `:nth-of-type(${sibs.indexOf(cur) + 1})`;
      }
      parts.unshift(seg);
      cur = p; depth++;
    }
    return parts.join('>');
  };

  document.querySelectorAll('[data-uix]').forEach(e => e.removeAttribute('data-uix'));

  const out = [];
  let n = 0;
  for (const el of document.querySelectorAll(SEL)) {
    if (!isVisible(el) || !inViewport(el)) continue;

    // collapse wrapper/child pairs that expose the same name
    const parentMarked = el.parentElement && el.parentElement.closest('[data-uix]');
    if (parentMarked && nameOf(parentMarked) === nameOf(el)) continue;

    if (++n > MAX) break;
    el.setAttribute('data-uix', String(n));
    const r = el.getBoundingClientRect();
    const isTextish = el.tagName === 'INPUT' || el.tagName === 'TEXTAREA';
    out.push({
      uix: n,
      role: roleOf(el),
      name: nameOf(el),
      tag: el.tagName.toLowerCase(),
      input_type: el.getAttribute('type'),
      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      checked: el.checked !== undefined ? el.checked : null,
      expanded: el.getAttribute('aria-expanded'),
      value: (isTextish && el.type !== 'password')
                ? String(el.value || '').slice(0, 60) : null,
      href: el.tagName === 'A' ? (el.getAttribute('href') || '').slice(0, 200) : null,
      path: cssPath(el),
      box: [Math.round(r.x), Math.round(r.y),
            Math.round(r.width), Math.round(r.height)],
    });
  }

  return {
    url: location.href, title: document.title,
    scroll_y: Math.round(scrollY),
    max_scroll: Math.round(document.body.scrollHeight),
    elements: out,
  };
})()