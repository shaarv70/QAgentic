import time
from utils.logger import logger


class DOMCaptureService:
    """
    Launches a headless Chrome browser, navigates to a URL, and returns
    a focused summary of interactive DOM elements.

    Used by SelfHealingAgent to give the LLM real element ids/names/classes
    when fixing broken locators instead of making it guess from test code alone.
    """

    def __init__(self, page_load_timeout: int = 15, render_wait: float = 2.0):
        self.page_load_timeout = page_load_timeout
        self.render_wait = render_wait

    def capture(self, url: str) -> str:
        """
        Open `url` in a headless browser and return a locator-focused DOM summary.

        Returns an empty string if Selenium is unavailable, the URL is
        unreachable, or any other error occurs — callers must handle gracefully.
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError:
            logger.warning("DOMCaptureService: selenium not installed — skipping DOM capture")
            return ""

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.get(url)

            # Brief wait for JS-rendered content
            if self.render_wait > 0:
                time.sleep(self.render_wait)

            page_source = driver.page_source
            summary = self._summarise_dom(page_source)

            logger.info(
                "DOMCaptureService: captured DOM | url=%s | elements=%d chars",
                url,
                len(summary),
            )
            return summary

        except Exception as exc:
            logger.warning(
                "DOMCaptureService: failed to capture DOM from %s — %s",
                url,
                exc,
            )
            return ""

        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    @staticmethod
    def _summarise_dom(html: str) -> str:
        """
        Extract locator-relevant attributes from interactive elements.

        Returns a compact text representation of up to 200 interactive
        elements — enough for the LLM to pick the right locator without
        being overwhelmed by the full HTML.
        """
        try:
            from html.parser import HTMLParser

            _INTERACTIVE_TAGS = {
                "input", "button", "a", "select", "textarea",
                "label", "form", "span", "div", "li", "td",
            }
            _LOCATOR_ATTRS = {
                "id", "name", "class", "type", "placeholder",
                "href", "value", "for", "aria-label", "data-testid",
                "role", "title", "alt",
            }
            _MAX_ELEMENTS = 200

            class _Extractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.elements = []
                    self._current_tag = None
                    self._current_text_parts = []
                    self._collecting = False

                def handle_starttag(self, tag, attrs):
                    if tag.lower() not in _INTERACTIVE_TAGS:
                        return
                    attr_dict = {k: v for k, v in attrs if v}
                    relevant = {
                        k: v for k, v in attr_dict.items()
                        if k in _LOCATOR_ATTRS
                    }
                    if relevant or tag.lower() in {"button", "a"}:
                        self._current_tag = tag
                        self._current_text_parts = []
                        self._collecting = True
                        self._pending = relevant

                def handle_data(self, data):
                    if self._collecting:
                        text = data.strip()
                        if text:
                            self._current_text_parts.append(text)

                def handle_endtag(self, tag):
                    if self._collecting and tag.lower() == self._current_tag:
                        self._collecting = False
                        attrs = dict(self._pending)
                        text = " ".join(self._current_text_parts)[:80]
                        if text:
                            attrs["text"] = text
                        if attrs and len(self.elements) < _MAX_ELEMENTS:
                            attr_str = " ".join(
                                f'{k}="{v}"' for k, v in attrs.items()
                            )
                            self.elements.append(
                                f"<{self._current_tag} {attr_str} />"
                            )

            extractor = _Extractor()
            extractor.feed(html)

            if not extractor.elements:
                # Fallback: return truncated raw HTML
                return html[:4000]

            return (
                "INTERACTIVE ELEMENTS (id, name, class, type, text, aria-label …):\n"
                + "\n".join(extractor.elements)
            )

        except Exception:
            return html[:4000]
