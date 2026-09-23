// No browser test dependency: execute the real script with the DOM surface used by the switcher.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/site.js'), 'utf8');

function load(cookie, options = {}) {
  const handlers = {};
  const classes = () => {
    const names = new Set();
    return {add(name) { names.add(name); }, contains(name) { return names.has(name); }, toggle() {}};
  };
  const element = () => ({
    attributes: {}, classList: classes(),
    setAttribute(key, value) { this.attributes[key] = value; },
    addEventListener(event, handler) { this[event] = handler; }
  });
  const burger = element();
  const mobile = element();
  const headline = {textContent: 'English', getAttribute: () => 'heading'};
  const root = {lang: 'en', classList: classes(), getAttribute: () => 'polyglot_lang'};
  const document = {
    cookie, documentElement: root, body: element(),
    getElementById(id) {
      return {burger, mobile, 'i18n-data': {textContent: JSON.stringify({uk: {heading: 'Українська'}})}}[id] || null;
    },
    querySelectorAll(selector) {
      if (selector === '[data-i18n]') return [headline];
      return selector.includes('#about .section-title') ? (options.revealItems || []) : [];
    },
    addEventListener(event, handler) { handlers[event] = handler; }
  };
  vm.runInNewContext(source, {
    document, location: {protocol: 'https:'},
    localStorage: {getItem: () => null, removeItem() {}},
    window: {
      addEventListener() {}, innerHeight: 800,
      matchMedia: () => ({matches: !!options.reducedMotion}),
      ...(options.IntersectionObserver ? {IntersectionObserver: options.IntersectionObserver} : {})
    }
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

test('scroll reveal observes offscreen content once and skips reduced motion', () => {
  const observed = [];
  const unobserved = [];
  let deliver;
  class Observer {
    constructor(callback) { deliver = (item) => callback([{target: item, isIntersecting: true}], this); }
    observe(item) { observed.push(item); }
    unobserve(item) { unobserved.push(item); }
  }
  const makeItem = () => {
    const names = new Set();
    return {
      classList: {add(name) { names.add(name); }, contains(name) { return names.has(name); }},
      getBoundingClientRect: () => ({top: 1000})
    };
  };
  const item = makeItem();
  const {root} = load('', {revealItems: [item], IntersectionObserver: Observer});
  assert.equal(root.classList.contains('motion-ready'), true);
  assert.deepEqual(observed, [item]);
  assert.equal(item.classList.contains('is-visible'), false);
  deliver(item);
  assert.equal(item.classList.contains('is-visible'), true);
  assert.deepEqual(unobserved, [item]);

  const reducedItem = makeItem();
  const reduced = load('', {revealItems: [reducedItem], IntersectionObserver: Observer, reducedMotion: true});
  assert.equal(reduced.root.classList.contains('motion-ready'), false);
  assert.equal(reducedItem.classList.contains('reveal'), false);
});
