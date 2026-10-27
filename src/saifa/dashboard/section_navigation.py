"""In-page section navigation without a Streamlit rerun on link clicks."""

import re
from collections.abc import Sequence

import streamlit as st

_ID = re.compile(r"[a-z][a-z0-9-]*\Z")

# Keep each heading visible below the fixed bar after browser-native scrolling.
_PAGE_STYLE = """
<style>
.st-key-saifa-section-nav {
    margin-bottom: 0.5rem;
}
__TARGETS__ {
    scroll-margin-top: 8rem;
}
@media (max-width: 640px) {
    __TARGETS__ { scroll-margin-top: 7.5rem; }
}
</style>
"""

_HTML = """
<nav class="section-nav" aria-label="Page sections">
  <a class="nav-pinned" hidden></a>
  <div class="nav-links"></div>
</nav>
"""

_CSS = """
:host { display: block; width: 100%; min-height: 3.2rem; }
.section-nav {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    min-width: 0;
    min-height: 3.2rem;
    box-sizing: border-box;
    position: fixed;
    top: 3.5rem;
    z-index: 1000;
    padding: 0.2rem 0;
    background: var(--st-background-color, #FAFBFC);
    border-bottom: 1px solid var(--st-border-color, #D8E1E7);
    color: var(--st-text-color, #183047);
    font-family: var(--st-font, sans-serif);
}
.nav-links {
    display: flex;
    flex: 1;
    min-width: 0;
    overflow-x: auto;
    white-space: nowrap;
    scrollbar-width: thin;
}
.nav-pinned,
.nav-links a {
    display: inline-block;
    flex: none;
    padding: 0.52rem 0.72rem 0.42rem;
    border-bottom: 2px solid transparent;
    color: var(--st-text-color, #183047);
    font-size: 0.86rem;
    text-decoration: none;
}
.nav-pinned { border-right: 1px solid var(--st-border-color, #D8E1E7); }
.nav-pinned[hidden] { display: none; }
.nav-pinned:hover,
.nav-pinned:focus-visible,
.nav-links a:hover,
.nav-links a:focus-visible {
    color: var(--st-primary-color, #137C73);
    background: var(--st-secondary-background-color, #ECF1F4);
}
.nav-pinned:focus-visible,
.nav-links a:focus-visible { outline: 2px solid var(--st-primary-color, #137C73); }
.nav-pinned[aria-current="location"],
.nav-links a[aria-current="location"] {
    color: var(--st-primary-color, #137C73);
    border-bottom-color: var(--st-primary-color, #137C73);
    font-weight: 600;
}
@media (max-width: 640px) {
    .section-nav { top: 3rem; }
    .nav-pinned,
    .nav-links a { padding-inline: 0.62rem; }
}
"""

_JS = """
export default function(component) {
    const { data, parentElement } = component;
    const previous = parentElement.__saifaNavCleanup;
    if (previous) previous();

    const nav = parentElement.querySelector(".section-nav");
    const row = nav?.querySelector(".nav-links");
    const pinnedLink = nav?.querySelector(".nav-pinned");
    if (!nav || !row || !pinnedLink) return;
    nav.setAttribute("aria-label", data?.aria_label ?? "Page sections");
    const host = parentElement.host ?? parentElement;
    const sections = data?.sections ?? [];
    row.replaceChildren();
    const links = new Map();
    const pinnedSection = sections.find(section => section.id === data?.pinned_id);
    pinnedLink.hidden = !pinnedSection;
    if (pinnedSection) {
        pinnedLink.href = `#${pinnedSection.id}`;
        pinnedLink.dataset.target = pinnedSection.id;
        pinnedLink.textContent = pinnedSection.label;
        links.set(pinnedSection.id, pinnedLink);
    }
    for (const section of sections) {
        if (section.id === pinnedSection?.id) continue;
        const link = document.createElement("a");
        link.href = `#${section.id}`;
        link.dataset.target = section.id;
        link.textContent = section.label;
        row.appendChild(link);
        links.set(section.id, link);
    }

    let activeId = null;
    function setActive(id) {
        if (id === activeId) return;
        activeId = id;
        for (const [key, link] of links) {
            if (key === id) link.setAttribute("aria-current", "location");
            else link.removeAttribute("aria-current");
        }
        const active = links.get(id);
        if (active && row.contains(active)) {
            const bounds = active.getBoundingClientRect();
            const viewport = row.getBoundingClientRect();
            if (bounds.left < viewport.left) row.scrollLeft -= viewport.left - bounds.left;
            if (bounds.right > viewport.right) row.scrollLeft += bounds.right - viewport.right;
        }
    }

    function scrollRoot(element) {
        for (let node = element.parentElement; node; node = node.parentElement) {
            const overflow = getComputedStyle(node).overflowY;
            if (/(auto|scroll)/.test(overflow) && node.scrollHeight > node.clientHeight) {
                return node;
            }
        }
        return document.scrollingElement;
    }

    function syncLayout() {
        const bounds = host.getBoundingClientRect();
        nav.style.left = `${bounds.left}px`;
        nav.style.width = `${bounds.width}px`;
    }

    let boundRoot = null;
    let sectionObserver = null;
    function updateActive() {
        syncLayout();
        const targets = sections.map(section => document.getElementById(section.id));
        if (!targets.every(Boolean)) return;
        const root = scrollRoot(targets[0]);
        if (root !== boundRoot) {
            if (boundRoot) boundRoot.removeEventListener("scroll", scheduleActive);
            boundRoot = root;
            if (boundRoot) boundRoot.addEventListener("scroll", scheduleActive, { passive: true });
        }
        if (!sectionObserver) {
            sectionObserver = new IntersectionObserver(scheduleActive, {
                root: null,
                rootMargin: "-120px 0px -65% 0px",
                threshold: 0
            });
            targets.forEach(target => sectionObserver.observe(target));
        }
        const atBottom = root && root.scrollHeight > root.clientHeight + 1 &&
            root.scrollTop + root.clientHeight >= root.scrollHeight - 12;
        const threshold = Math.max(120, nav.getBoundingClientRect().bottom + 40);
        let current = sections[0]?.id;
        for (let index = 0; index < targets.length; index++) {
            if (targets[index].getBoundingClientRect().top <= threshold) {
                current = sections[index].id;
            }
        }
        if (atBottom) current = sections[sections.length - 1]?.id;
        setActive(current);
    }

    let frame = 0;
    function scheduleActive() {
        if (frame) return;
        frame = requestAnimationFrame(() => {
            frame = 0;
            updateActive();
        });
    }

    function onClick(event) {
        const link = event.target.closest?.("a[data-target]");
        if (!link) return;
        event.preventDefault();
        const id = link.dataset.target;
        const target = document.getElementById(id);
        if (!target) return;
        const behavior = matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
        target.scrollIntoView({ behavior, block: "start" });
        setActive(id);
    }

    nav.addEventListener("click", onClick);
    document.addEventListener("scroll", scheduleActive, { capture: true, passive: true });
    window.addEventListener("scroll", scheduleActive, { passive: true });
    window.addEventListener("resize", scheduleActive);
    const resizeObserver = new ResizeObserver(scheduleActive);
    resizeObserver.observe(host);
    const observer = new MutationObserver(() => {
        scheduleActive();
        if (sections.every(section => document.getElementById(section.id))) observer.disconnect();
    });
    if (document.body) observer.observe(document.body, { childList: true, subtree: true });
    setActive(links.has(location.hash.slice(1)) ? location.hash.slice(1) : sections[0]?.id);
    scheduleActive();

    const cleanup = () => {
        nav.removeEventListener("click", onClick);
        document.removeEventListener("scroll", scheduleActive, true);
        window.removeEventListener("scroll", scheduleActive);
        window.removeEventListener("resize", scheduleActive);
        if (boundRoot) boundRoot.removeEventListener("scroll", scheduleActive);
        if (sectionObserver) sectionObserver.disconnect();
        resizeObserver.disconnect();
        observer.disconnect();
        if (frame) cancelAnimationFrame(frame);
        if (parentElement.__saifaNavCleanup === cleanup) delete parentElement.__saifaNavCleanup;
    };
    parentElement.__saifaNavCleanup = cleanup;
    return cleanup;
}
"""

_NAV = st.components.v2.component("saifa_section_navigation", html=_HTML, css=_CSS, js=_JS)


def render_section_navigation(
    sections: Sequence[tuple[str, str]],
    *,
    pinned_id: str | None = None,
    aria_label: str = "Page sections",
) -> None:
    """Render a compact page-section bar fixed above the page content."""
    if not sections or any(
        not _ID.fullmatch(section_id) or not label for section_id, label in sections
    ):
        raise ValueError("Section navigation needs nonempty labels and safe IDs")
    if len({section_id for section_id, _ in sections}) != len(sections):
        raise ValueError("Section navigation IDs must be unique")
    if pinned_id is not None and pinned_id not in {section_id for section_id, _ in sections}:
        raise ValueError("Pinned section must be a navigation target")
    if not aria_label.strip():
        raise ValueError("Section navigation needs an accessible label")
    selectors = ",\n".join(f"#{section_id}" for section_id, _ in sections)
    st.html(_PAGE_STYLE.replace("__TARGETS__", selectors))
    with st.container(key="saifa-section-nav"):
        _NAV(
            key="saifa-section-links",
            data={
                "sections": [{"id": section_id, "label": label} for section_id, label in sections],
                "pinned_id": pinned_id,
                "aria_label": aria_label,
            },
        )
