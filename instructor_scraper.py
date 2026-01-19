"""
Instructor/Professor scraper using ONLY Firecrawl for RateMyProfessors
NO MOCK DATA - Live scraping only
"""

from firecrawl import FirecrawlApp
from typing import Dict, Optional, List
import re


class InstructorScraper:
    """
    Scrapes professor information from RateMyProfessors using Firecrawl
    """

    def __init__(self, firecrawl_api_key: str):
        """
        Initialize with Firecrawl API key

        Args:
            firecrawl_api_key: Firecrawl API key (required)
        """
        if not firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY is required for InstructorScraper")

        self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)
        self.rmp_base_url = "https://www.ratemyprofessors.com"

        print(f"✅ InstructorScraper initialized with Firecrawl")

    # -------------------------
    # Matching helpers
    # -------------------------
    def _normalize_text(self, s: str) -> str:
        """Lowercase + strip punctuation for robust substring matching."""
        return re.sub(r"[^a-z0-9\s]", " ", (s or "").lower())

    def _distinctive_uni_tokens(self, university: str) -> List[str]:
        """Return meaningful tokens from a university name (drop generic words)."""
        stop = {
            "university", "college", "institute", "school", "of", "the", "and",
            "at", "in", "state", "campus", "department", "faculty"
        }
        tokens = [
            t for t in self._normalize_text(university).split()
            if len(t) >= 4 and t not in stop
        ]
        # Deduplicate while keeping order
        return list(dict.fromkeys(tokens))

    def _university_matches(self, profile_text: str, university: str) -> bool:
        """True if any distinctive token from the university appears in profile text."""
        text = self._normalize_text(profile_text)
        tokens = self._distinctive_uni_tokens(university)
        if not tokens:
            return False
        return any(t in text for t in tokens)

    def search_professor(self, professor_name: str, university: str) -> Dict:
        """
        Search for a professor on RateMyProfessors

        Args:
            professor_name: Name of the professor
            university: University name

        Returns:
            Dictionary with professor information from RateMyProfessors
        """
        try:
            print(f"🔍 Searching RateMyProfessors for {professor_name} at {university}...")

            search_name = professor_name.replace(" ", "%20")
            search_uni = university.replace(" ", "%20")
            search_url = f"{self.rmp_base_url}/search/professors?q={search_name}%20{search_uni}"

            print(f"🔥 Scraping with Firecrawl: {search_url}")

            # RMP search pages often hide profile links outside "main content".
            result = self.firecrawl.scrape_url(
                search_url,
                params={
                    "formats": ["markdown", "html"],
                    "onlyMainContent": False,
                },
            )

            markdown = (result.get("markdown", "") or "") + "\n" + (result.get("html", "") or "")
            print(f"📄 Search results preview: {markdown[:500]}...")

            # Collect candidate IDs and verify by scraping each profile.
            profile_ids = re.findall(r"/professor/(\d+)", markdown)
            profile_ids = list(dict.fromkeys(profile_ids))  # dedupe, preserve order

            if not profile_ids:
                return {
                    "name": professor_name,
                    "university": university,
                    "source": "RateMyProfessors (via Firecrawl)",
                    "error": f"Could not find any professor profiles in search results for '{professor_name}'.",
                }

            print(f"🔍 Found {len(profile_ids)} candidate profiles. Verifying university match for {university}...")

            checked = 0
            for prof_id in profile_ids[:10]:
                checked += 1
                profile_url = f"{self.rmp_base_url}/professor/{prof_id}"
                print(f"   🔎 Checking candidate {checked}: {profile_url}")

                profile_data = self._scrape_professor_profile(profile_url)
                raw = profile_data.get("raw_markdown", "")

                if raw and self._university_matches(raw, university):
                    print(f"✅ Matched university for profile {prof_id}")
                    profile_data["profile_url"] = profile_url
                    profile_data["name"] = professor_name
                    profile_data["university"] = university
                    profile_data["source"] = "RateMyProfessors (via Firecrawl)"
                    return profile_data

            # If none match, try name-only query and filter again.
            print(f"⚠️  No university match found in top {checked} candidates. Trying alternative search...")
            alt_result = self._search_alternative(professor_name, university)
            if alt_result and "error" not in alt_result:
                return alt_result

            return {
                "name": professor_name,
                "university": university,
                "source": "RateMyProfessors (via Firecrawl)",
                "error": (
                    f"Could not find a RateMyProfessors profile for {professor_name} at {university} "
                    f"(checked {checked} candidates from search results)."
                ),
            }

        except Exception as e:
            return {
                "name": professor_name,
                "university": university,
                "error": f"Error scraping RateMyProfessors: {str(e)}"
            }

    def _search_alternative(self, professor_name: str, university: str) -> Optional[Dict]:
        """
        Alternative search strategy when first attempt fails.
        Searches name-only then filters by university.
        """
        try:
            search_name = professor_name.replace(" ", "%20")
            search_url = f"{self.rmp_base_url}/search/professors?q={search_name}"

            print(f"🔄 Alternative search: {search_url}")

            result = self.firecrawl.scrape_url(
                search_url,
                params={
                    "formats": ["markdown", "html"],
                    "onlyMainContent": False,
                },
            )

            markdown = (result.get("markdown", "") or "") + "\n" + (result.get("html", "") or "")

            all_ids = re.findall(r"/professor/(\d+)", markdown)
            all_ids = list(dict.fromkeys(all_ids))

            print(f"🔍 Found {len(all_ids)} profiles, checking each for {university}...")

            checked = 0
            for prof_id in all_ids[:10]:
                checked += 1
                profile_url = f"{self.rmp_base_url}/professor/{prof_id}"
                print(f"   🔎 Checking alternative candidate {checked}: {profile_url}")

                profile_data = self._scrape_professor_profile(profile_url)
                raw = profile_data.get("raw_markdown", "")

                if raw and self._university_matches(raw, university):
                    print(f"✅ Found match via alternative search: {prof_id}")
                    profile_data["profile_url"] = profile_url
                    profile_data["name"] = professor_name
                    profile_data["university"] = university
                    profile_data["source"] = "RateMyProfessors (via Firecrawl)"
                    return profile_data

            return None

        except Exception as e:
            print(f"Alternative search failed: {e}")
            return None

    def _parse_search_results_improved(self, markdown: str, professor_name: str, university: str) -> Dict:
        """
        Parse search results with improved filtering for university match
        """
        # Extract all professor profile links
        professor_links = re.findall(r'https://www\.ratemyprofessors\.com/professor/\d+', markdown)

        # Remove duplicates
        professor_links = list(set(professor_links))

        print(f"🔍 Found {len(professor_links)} potential professor profiles")

        # If no links found, try alternative regex patterns
        if not professor_links:
            # Try different patterns
            professor_ids = re.findall(r'/professor/(\d+)', markdown)
            professor_ids = list(set(professor_ids))

            for prof_id in professor_ids:
                professor_links.append(f"{self.rmp_base_url}/professor/{prof_id}")

            print(f"🔍 Alternative pattern found {len(professor_links)} profiles")

        # Filter results by professor name and university if possible
        best_match = None
        best_score = 0

        for link in professor_links[:5]:  # Check top 5 results
            print(f"🔍 Checking profile: {link}")

            # Scrape basic profile info to verify university
            profile_data = self._scrape_professor_profile(link)
            scraped_content = profile_data.get('raw_markdown', '').lower()

            # Score based on university match
            university_keywords = [word for word in university.lower().split() if len(word) > 3]
            score = sum(1 for keyword in university_keywords if keyword in scraped_content)

            if score > best_score:
                best_score = score
                best_match = link

                # If perfect match found, stop searching
                if score >= len(university_keywords) * 0.5:  # At least 50% match
                    break

        if best_match:
            print(f"✅ Best match found: {best_match} (score: {best_score})")
            return {"profile_url": best_match}
        else:
            print(f"❌ No good match found for {university}")
            return {"error": f"No matching professor found for {university}"}

    def _scrape_professor_profile(self, profile_url: str) -> Dict:
        """
        Scrape a professor profile page
        """
        try:
            print(f"🔥 Scraping full profile: {profile_url}")

            result = self.firecrawl.scrape_url(
                profile_url,
                params={
                    'formats': ['markdown'],
                    'onlyMainContent': True
                }
            )

            markdown = result.get('markdown', '')

            if not markdown:
                return {"error": "No profile data found"}

            # Parse the profile data
            profile_data = self._parse_profile_data(markdown)

            # Add raw markdown for AI analysis
            profile_data['raw_markdown'] = markdown

            print(f"✅ Successfully scraped profile")
            return profile_data

        except Exception as e:
            return {"error": f"Error scraping profile: {str(e)}"}

    def _parse_profile_data(self, markdown: str) -> Dict:
        """
        Parse professor profile data from markdown
        """
        data = {}

        try:
            # Extract overall rating
            rating_match = re.search(r'Overall Quality\s*([\d\.]+)', markdown)
            if rating_match:
                data['overall_rating'] = rating_match.group(1)

            # Extract difficulty
            difficulty_match = re.search(r'Difficulty\s*([\d\.]+)', markdown)
            if difficulty_match:
                data['difficulty'] = difficulty_match.group(1)

            # Extract would take again
            take_again_match = re.search(r'Would Take Again\s*([\d%]+)', markdown)
            if take_again_match:
                data['would_take_again'] = take_again_match.group(1)

            # Extract number of ratings
            num_ratings_match = re.search(r'(\d+)\s+Ratings', markdown)
            if num_ratings_match:
                data['num_ratings'] = int(num_ratings_match.group(1))
            else:
                data['num_ratings'] = 0

            # Extract top tags if available
            tags_section = re.search(r'Top Tags\s*(.*?)(?:\n\n|\Z)', markdown, re.DOTALL)
            if tags_section:
                tags_text = tags_section.group(1)
                tags = re.findall(r'-\s*([^\n]+)', tags_text)
                data['top_tags'] = tags[:10]  # Top 10 tags

            # Extract reviews/comments
            reviews = []
            review_sections = re.findall(r'Rating\s*Comment\s*(.*?)(?=Rating\s*Comment|\Z)', markdown, re.DOTALL)

            for section in review_sections[:5]:  # Limit to 5 most recent reviews
                # Extract comment text
                comment_match = re.search(r'Comment\s*(.*?)(?:\n|$)', section, re.DOTALL)
                if comment_match:
                    comment = comment_match.group(1).strip()
                    if comment and len(comment) > 10:
                        reviews.append(comment)

            data['recent_reviews'] = reviews

            return data

        except Exception as e:
            return {"error": f"Error parsing profile data: {str(e)}"}

    def scrape_by_url(self, rmp_url: str) -> Dict:
        """
        Scrape professor data directly from a known RateMyProfessors URL

        Args:
            rmp_url: Direct URL to professor profile

        Returns:
            Professor data dictionary
        """
        if not rmp_url or "ratemyprofessors.com/professor/" not in rmp_url:
            return {"error": "Invalid RateMyProfessors URL"}

        # Scrape the profile directly
        return self._scrape_professor_profile(rmp_url)


def test_scraper():
    """
    Test the InstructorScraper
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    if not firecrawl_key:
        print("❌ FIRECRAWL_API_KEY not found in environment variables")
        return

    scraper = InstructorScraper(firecrawl_key)

    # Test with a known professor
    print("\n\n📋 Test 1: Search Professor")
    print("="*70)
    prof_name = input("Enter professor name to test (e.g., 'John Smith'): ")
    university = input("Enter university name (e.g., 'University of Alberta'): ")

    result = scraper.search_professor(prof_name, university)

    print("\n📊 Results:")
    print("-"*70)
    for key, value in result.items():
        if key != 'raw_markdown':  # Don't print full markdown
            print(f"{key}: {value}")

    # Test with direct URL (if you have one)
    print("\n\n📋 Test 2: Scrape by Direct URL")
    print("="*70)
    print("⚠️  Provide a known RMP URL to test this feature")

    print("\n" + "="*70)
    print("✅ Test Complete!")


if __name__ == "__main__":
    test_scraper()
