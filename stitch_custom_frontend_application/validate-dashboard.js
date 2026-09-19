#!/usr/bin/env node
/**
 * validate-dashboard.js
 * Standalone validation script for the Autopilot Web Journey Agent frontend.
 * Conforms to FRONTEND_DETAIL.txt sec 1.7 and FRONTEND_RULES.md.
 *
 * Plain Node, zero dependencies - run with: node validate-dashboard.js
 *
 * Checks, per page:
 *   1. Exactly one <main>, no duplicate id attributes.
 *   2. Every required data-testid hook for that route is present.
 *   3. No external framework/CDN <script src> or <link rel=stylesheet href>
 *      besides Google Fonts.
 *   4. Every <img> has non-empty alt text.
 *   5. Every <button>/<a> has visible text or an aria-label/title.
 *   6. No raw internal jargon in visible body text.
 *
 * Prints PASS/FAIL per built page and exits non-zero if anything failed.
 * Routes with no HTML file yet are reported as SKIP, not FAIL - they simply
 * haven't been built, which isn't a defect in an existing page.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = __dirname;

const PAGES = [
  {
    route: '#/',
    name: 'Home Dashboard',
    file: 'autopilot_home_dashboard/code.html',
    requiredHooks: ['scenario-card', 'quick-stats', 'recent-runs-table', 'btn-start-new-journey'],
  },
  { route: '#/run/new', name: 'New Journey Wizard', file: null, requiredHooks: [] },
  { route: '#/run/:run_id', name: 'Live Journey Monitor', file: null, requiredHooks: [] },
  {
    route: '#/run/:run_id/report',
    name: 'Full Report Viewer',
    file: 'autopilot_full_report_viewer/code.html',
    requiredHooks: ['report-header', 'executive-summary', 'metrics-grid', 'findings-section', 'chronological-audit', 'artifacts-section'],
  },
  { route: '#/history', name: 'Run History', file: null, requiredHooks: [] },
  {
    route: '#/settings',
    name: 'Settings & Scenarios',
    file: 'autopilot_settings_scenarios/code.html',
    requiredHooks: ['table-scenarios-list', 'section-execution-profiles', 'section-safety-guardrails', 'section-storage-management'],
  },
];

const FORBIDDEN_JARGON = [
  'uix-', 'state hash', 'stuck_loop', 'same state hash', 'perceiving dom', 'policy gate blocked action class',
];
// Only Google Fonts is an allowed external host - everything else must be vanilla/local.
const ALLOWED_EXTERNAL_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

function extractTags(html, tagName) {
  return html.match(new RegExp(`<${tagName}\\b[^>]*>`, 'gi')) || [];
}

function attr(tag, name) {
  const m = tag.match(new RegExp(`${name}\\s*=\\s*"([^"]*)"`, 'i')) || tag.match(new RegExp(`${name}\\s*=\\s*'([^']*)'`, 'i'));
  return m ? m[1] : null;
}

function stripTags(html) {
  return html
    .replace(/<script\b[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function validatePage(page) {
  const result = { route: page.route, name: page.name, checks: [] };
  const record = (pass, message) => result.checks.push({ pass, message });

  if (!page.file) {
    result.skipped = true;
    result.reason = 'Route not built yet - no HTML file exists for this page.';
    return result;
  }

  const filePath = path.join(ROOT, page.file);
  if (!fs.existsSync(filePath)) {
    record(false, `File not found: ${page.file}`);
    return result;
  }
  const html = fs.readFileSync(filePath, 'utf8');

  const mainCount = (html.match(/<main\b/gi) || []).length;
  record(mainCount === 1, `Exactly one <main> element (found ${mainCount})`);

  const ids = (html.match(/\bid\s*=\s*"([^"]*)"/gi) || []).map((t) => t.match(/"([^"]*)"/)[1]);
  const seen = new Set();
  const dupes = new Set();
  ids.forEach((id) => { if (seen.has(id)) dupes.add(id); seen.add(id); });
  record(dupes.size === 0, `No duplicate id attributes (found: ${[...dupes].join(', ') || 'none'})`);

  page.requiredHooks.forEach((hook) => {
    const present = html.includes(`data-testid="${hook}"`) || html.includes(`data-testid='${hook}'`);
    record(present, `Required hook data-testid="${hook}" is present`);
  });

  extractTags(html, 'script').forEach((tag) => {
    const src = attr(tag, 'src');
    if (!src || !/^https?:\/\//i.test(src)) return;
    const allowed = ALLOWED_EXTERNAL_HOSTS.some((host) => src.includes(host));
    record(allowed, `No disallowed external script (found: ${src})`);
  });

  extractTags(html, 'link').forEach((tag) => {
    if ((attr(tag, 'rel') || '').toLowerCase() !== 'stylesheet') return;
    const href = attr(tag, 'href') || '';
    if (!/^https?:\/\//i.test(href)) return;
    const allowed = ALLOWED_EXTERNAL_HOSTS.some((host) => href.includes(host));
    record(allowed, `External stylesheet is an allowed Google Fonts link (found: ${href})`);
  });

  extractTags(html, 'img').forEach((tag, i) => {
    const alt = attr(tag, 'alt');
    record(!!(alt && alt.trim()), `Image #${i + 1} has non-empty alt text`);
  });

  ['button', 'a'].forEach((tagName) => {
    const tags = html.match(new RegExp(`<${tagName}\\b[^>]*>([\\s\\S]*?)<\\/${tagName}>`, 'gi')) || [];
    tags.forEach((full, i) => {
      const openTag = (full.match(new RegExp(`^<${tagName}\\b[^>]*>`, 'i')) || [full])[0];
      const inner = full.slice(openTag.length, full.length - (`</${tagName}>`).length);
      const text = stripTags(inner);
      const accessible = text || attr(openTag, 'aria-label') || attr(openTag, 'title');
      record(!!accessible, `${tagName} #${i + 1} has visible text or an aria-label/title`);
    });
  });

  const visibleText = stripTags(html).toLowerCase();
  FORBIDDEN_JARGON.forEach((token) => {
    record(!visibleText.includes(token), `No raw jargon "${token}" in visible text`);
  });

  return result;
}

function main() {
  console.log('====================================================');
  console.log(' AUTOPILOT DASHBOARD VALIDATION');
  console.log('====================================================');

  let totalFailed = 0;
  let builtPages = 0;

  PAGES.forEach((page) => {
    const result = validatePage(page);
    if (result.skipped) {
      console.log(`\n[SKIP] ${result.name} (${result.route}) - ${result.reason}`);
      return;
    }
    builtPages++;
    const failed = result.checks.filter((c) => !c.pass);
    console.log(`\n[${failed.length === 0 ? 'PASS' : 'FAIL'}] ${result.name} (${result.route}) - ${result.checks.length - failed.length}/${result.checks.length} checks passed`);
    failed.forEach((c) => console.log(`   FAIL: ${c.message}`));
    totalFailed += failed.length;
  });

  console.log('\n====================================================');
  console.log(totalFailed === 0
    ? ` ALL ${builtPages} BUILT PAGE(S) PASSED`
    : ` ${totalFailed} CHECK(S) FAILED ACROSS ${builtPages} BUILT PAGE(S)`);
  console.log('====================================================');

  process.exit(totalFailed === 0 ? 0 : 1);
}

main();
