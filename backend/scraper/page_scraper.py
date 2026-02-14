from dataclasses import dataclass, field
import httpx
from bs4 import BeautifulSoup


@dataclass
class ScrapedPage:
    url: str
    title: str = ""
    text_content: str = ""
    images: list[str] = field(default_factory=list)
    meta_description: str = ""
    success: bool = False
    error: str = ""


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}


async def scrape_page(url: str, timeout: float = 30.0) -> ScrapedPage:
    """Scrape a product page and extract key content.

    Args:
        url: The URL to scrape.
        timeout: Request timeout in seconds.

    Returns:
        ScrapedPage with extracted content.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        # Extract main text content (truncate to avoid huge pages)
        text = soup.get_text(separator="\n", strip=True)
        # Keep first 15000 chars to stay within LLM context
        text = text[:15000]

        # Extract image URLs
        images = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                # Build absolute URL
                from urllib.parse import urlparse
                parsed = urlparse(url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
            if any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                images.append(src)

        # Deduplicate images
        images = list(dict.fromkeys(images))[:20]  # Max 20 images

        return ScrapedPage(
            url=url,
            title=title,
            text_content=text,
            images=images,
            meta_description=meta_desc,
            success=True,
        )

    except Exception as e:
        return ScrapedPage(
            url=url,
            success=False,
            error=str(e),
        )
