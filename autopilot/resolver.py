from __future__ import annotations

from typing import Any, Optional
from playwright.sync_api import Locator, Page
from .types import ProposedAction, Observation, TargetDescriptor, Element


def _normalize_name(name: str) -> str:
    """Normalize name for comparison: casefold, collapse whitespace, strip punctuation."""
    import re
    return re.sub(r'[\W_]+', ' ', name.casefold()).strip()


class Resolver:
    def resolve(self, page: Page, proposed: ProposedAction, obs: Observation) -> tuple[Optional[Locator], Optional[TargetDescriptor], float, int]:
        if proposed.uix is None:
            return None, None, 0.0, 0
        
        # Find element by uix
        element = None
        for el in obs.elements:
            if el.uix == proposed.uix:
                element = el
                break
        
        if not element:
            return None, None, 0.0, 0
        
        # Re-capture inventory for the element's frame to score candidates
        frame = page.main_frame if element.frame_id == "main" else None
        if not frame:
            for f in page.frames:
                if f.url.split('/')[2] if '://' in f.url else 'unknown' == element.frame_id.split(':')[-1]:
                    frame = f
                    break
        
        if not frame:
            frame = page.main_frame
        
        # Re-capture inventory for scoring
        inventory_js = """
        () => {
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
                if (explicit) return explicit.split(/\\s+/)[0];
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
                return ids.split(/\\s+/).map(i => (document.getElementById(i) || {}).innerText || '').join(' ');
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
                    if (c && c.trim()) return c.trim().replace(/\\s+/g, ' ').slice(0, 120);
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
                const parentMarked = el.parentElement && el.parentElement.closest('[data-uix]');
                if (parentMarked && nameOf(parentMarked) === nameOf(el)) continue;
                if (++n > 120) break;
                el.setAttribute('data-uix', String(n));
                const r = el.getBoundingClientRect();
                const isTextish = el.tagName === 'INPUT' || el.tagName === 'TEXTAREA';
                out.push({
                    uix: n,
                    role: roleOf(el),
                    name: nameOf(el),
                    tag: el.tagName.toLowerCase(),
                    path: cssPath(el),
                });
            }
            return out;
        }
        """
        try:
            result = frame.evaluate(inventory_js)
            # Handle both list and dict-with-elements-key responses
            if isinstance(result, dict) and "elements" in result:
                candidates = result["elements"]
            else:
                candidates = result
        except Exception:
            candidates = []
        
        # Score candidates
        target_role = element.role
        target_name = element.name
        target_tag = element.tag
        target_path = element.path
        target_norm_name = _normalize_name(target_name)
        
        scored = []
        for c in candidates:
            score = 0
            if c.get('role') == target_role and c.get('name') == target_name and c.get('tag') == target_tag:
                score += 3
            if c.get('path') == target_path:
                score += 2
            if _normalize_name(c.get('name', '')) == target_norm_name:
                score += 1
            scored.append((score, c))
        
        scored.sort(key=lambda x: -x[0])
        candidates_considered = len(scored)
        
        if not scored or scored[0][0] < 3:
            return None, None, 0.0, candidates_considered
        
        # Check for tie without ordinal disambiguation
        ordinal = 0
        if len(scored) >= 2 and scored[0][0] == scored[1][0]:
            # Check if ordinal disambiguates - use ORIGINAL observation for ordinal
            # Ordinal is index among elements sharing (role, name, tag) at capture (per spec)
            same_elements = [el for el in obs.elements 
                           if el.role == target_role and el.name == target_name and el.tag == target_tag]
            if len(same_elements) >= 2:
                # Find ordinal of the target element among same elements
                for i, el in enumerate(same_elements):
                    if el.uix == proposed.uix:
                        ordinal = i + 1
                        break
            # If tie at max score (6) and multiple identical elements, reject as ambiguous
            if scored[0][0] >= 6 and len(same_elements) >= 2:
                return None, None, 0.0, candidates_considered
            if ordinal == 0:
                return None, None, 0.0, candidates_considered
        
        # Build descriptor from original element
        descriptor = TargetDescriptor(
            frame_id=element.frame_id,
            role=element.role,
            name=element.name,
            tag=element.tag,
            path=element.path,
            ordinal=ordinal,
        )
        
        locator = frame.locator(f'[data-uix="{proposed.uix}"]')
        
        return locator, descriptor, min(1.0, scored[0][0] / 6.0), candidates_considered


def resolve(page: Page, proposed: ProposedAction, obs: Observation) -> tuple[Optional[Locator], Optional[TargetDescriptor], float, int]:
    """Module-level resolve function for tests and external use."""
    resolver = Resolver()
    return resolver.resolve(page, proposed, obs)


def create_resolver() -> Resolver:
    return Resolver()