// No browser test dependency: execute the real script with the DOM surface used by the switcher.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/site.js'), 'utf8');

function load(cookie) {
  const handlers = {};
  const element = () => ({
    attributes: {}, classList: {toggle() {}},
    setAttribute(key, value) { this.attributes[key] = value; },
    addEventListener(event, handler) { this[event] = handler; }
  });
  const burger = element();
  const mobile = element();
  const headline = {textContent: 'English', getAttribute: () => 'heading'};
  const root = {lang: 'en', getAttribute: () => 'polyglot_lang'};
  const document = {
    cookie, documentElement: root, body: element(),
    getElementById(id) {
      return {burger, mobile, 'i18n-data': {textContent: JSON.stringify({uk: {heading: 'Українська'}})}}[id] || null;
    },
    querySelectorAll(selector) { return selector === '[data-i18n]' ? [headline] : []; },
    addEventListener(event, handler) { handlers[event] = handler; }
  };
  vm.runInNewContext(source, {
    document, location: {protocol: 'https:'},
    localStorage: {getItem: () => null, removeItem() {}},
    window: {addEventListener() {}}
  });
  return {document, root, headline, handlers, burger};
}

test('malformed percent-encoded cookie does not stop the mobile menu or language switcher', () => {
  const {document, root, headline, handlers, burger} = load('polyglot_lang=%E0%A4%A');
  burger.click();
  assert.equal(burger.attributes['aria-expanded'], 'true');
  handlers.keydown({key: 'Escape'});
  assert.equal(burger.attributes['aria-expanded'], 'false');
  handlers.click({target: {closest: () => ({getAttribute: () => 'uk'})}});
  assert.equal(root.lang, 'uk');
  assert.equal(headline.textContent, 'Українська');
  assert.match(document.cookie, /^polyglot_lang=uk; Max-Age=31536000; Path=\/; SameSite=Lax; Secure$/);
});

test('automatic server language is not saved as a manual preference', () => {
  const {document, handlers, root} = load('');
  assert.equal(document.cookie, '');
  handlers.click({target: {closest: () => ({getAttribute: () => 'unknown'})}});
  assert.equal(document.cookie, '');
  assert.equal(root.lang, 'en');
});
