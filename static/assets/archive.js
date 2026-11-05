(() => {
  "use strict";

  const form = document.querySelector("form[data-filters]");
  if (!form) return;

  const search = form.querySelector("[data-search]");
  const tagFilter = form.querySelector("[data-tag-filter]");
  const reset = form.querySelector("[data-reset]");
  if (!search || !tagFilter || !reset) return;

  const count = document.querySelector("[data-count]");
  const empty = document.querySelector("[data-empty]");
  const normalize = (value) => String(value || "").normalize("NFKC").trim().toLowerCase();
  const drafts = Array.from(document.querySelectorAll("article[data-draft]"), (element) => ({
    element,
    text: normalize(element.dataset.searchText || element.textContent),
    tags: (element.dataset.tags || "").split("|").map(normalize).filter(Boolean),
  }));

  function applyFilters() {
    const terms = normalize(search.value).split(/\s+/).filter(Boolean);
    const selectedTag = normalize(tagFilter.value);
    let visible = 0;

    drafts.forEach((draft) => {
      const matchesSearch = terms.every((term) => draft.text.includes(term));
      const matchesTag = !selectedTag || draft.tags.includes(selectedTag);
      const matches = matchesSearch && matchesTag;
      draft.element.hidden = !matches;
      if (matches) visible += 1;
    });

    if (count) {
      const noun = drafts.length === 1 ? "draft" : "drafts";
      count.textContent = terms.length || selectedTag
        ? `${visible} of ${drafts.length} ${noun} shown.`
        : `${drafts.length} ${noun}.`;
    }
    if (empty) empty.hidden = visible !== 0;
  }

  search.addEventListener("input", applyFilters);
  tagFilter.addEventListener("change", applyFilters);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    applyFilters();
  });
  reset.addEventListener("click", () => {
    search.value = "";
    tagFilter.value = "";
    applyFilters();
    search.focus();
  });

  if (count && !count.hasAttribute("aria-live")) count.setAttribute("aria-live", "polite");
  applyFilters();
  form.hidden = false;
})();
