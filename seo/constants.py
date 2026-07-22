from django.db import models
from django.utils.translation import gettext_lazy as _


class SeoSchemaType(models.TextChoices):
    """Schema.org tip primarnog sadržaja — prazno = automatski prema tipu stranice."""

    AUTO = "", _("Automatski (preporučeno)")
    ARTICLE = "Article", "Article"
    BLOG_POSTING = "BlogPosting", "BlogPosting"
    FAQ_PAGE = "FAQPage", "FAQPage"
    WEB_PAGE = "WebPage", "WebPage"
    PERSON = "Person", "Person"
    ORGANIZATION = "Organization", "Organization"
    # Legacy — zadržano radi postojećih zapisa u bazi
    SERVICE = "Service", "Service"
    ITEM_LIST = "ItemList", "ItemList"
    LOCAL_BUSINESS = "LocalBusiness", "LocalBusiness"


DEFAULT_BLOG_SCHEMA = SeoSchemaType.BLOG_POSTING
DEFAULT_PAGE_SCHEMA = SeoSchemaType.WEB_PAGE


class OgType(models.TextChoices):
    """Open Graph tip — prazno = automatski prema sadržaju."""

    AUTO = "", _("Automatski (preporučeno)")
    WEBSITE = "website", "website"
    ARTICLE = "article", "article"
    PRODUCT = "product", "product"
    PROFILE = "profile", "profile"
    VIDEO = "video.other", "video.other"


DEFAULT_BLOG_OG_TYPE = OgType.ARTICLE
DEFAULT_PAGE_OG_TYPE = OgType.WEBSITE

# Open Graph slike — preporuke Facebook / LinkedIn
OG_IMAGE_MIN_WIDTH = 200
OG_IMAGE_MIN_HEIGHT = 200
OG_IMAGE_RECOMMENDED_WIDTH = 1200
OG_IMAGE_RECOMMENDED_HEIGHT = 630
OG_IMAGE_MAX_BYTES = 8 * 1024 * 1024
OG_IMAGE_ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF", "JPG"})

SEO_TITLE_MAX_LENGTH = 70
META_DESCRIPTION_MAX_LENGTH = 320
KEYWORD_MAX_LENGTH = 100
SECONDARY_KEYWORDS_MAX_LENGTH = 255
BREADCRUMB_TITLE_MAX_LENGTH = 100

# Google SERP preview — preporučene dužine i prikaz
SERP_TITLE_IDEAL_MIN = 50
SERP_TITLE_IDEAL_MAX = 60
SERP_TITLE_DESKTOP_DISPLAY_MAX = 60
SERP_TITLE_MOBILE_DISPLAY_MAX = 55
SERP_DESCRIPTION_IDEAL_MIN = 120
SERP_DESCRIPTION_IDEAL_MAX = 160
SERP_DESCRIPTION_DESKTOP_DISPLAY_MAX = 160
SERP_DESCRIPTION_MOBILE_DISPLAY_MAX = 120

# Open Graph pregled po platformama — prikaz u admin panelu
OG_PLATFORM_PROFILES = {
    "facebook": {
        "label": "Facebook",
        "title_max": 60,
        "description_max": 160,
        "card_class": "seo-og-preview__card--facebook",
    },
    "linkedin": {
        "label": "LinkedIn",
        "title_max": 70,
        "description_max": 160,
        "card_class": "seo-og-preview__card--linkedin",
    },
    "whatsapp": {
        "label": "WhatsApp",
        "title_max": 65,
        "description_max": 90,
        "card_class": "seo-og-preview__card--whatsapp",
    },
}
DEFAULT_OG_PREVIEW_PLATFORM = "facebook"


class TwitterCardType(models.TextChoices):
    """Twitter Card tip — prazno = automatski prema slici."""

    AUTO = "", _("Automatski (preporučeno)")
    SUMMARY = "summary", "summary"
    SUMMARY_LARGE_IMAGE = "summary_large_image", "summary_large_image"


class RobotsMaxImagePreview(models.TextChoices):
    """Google max-image-preview direktiva — prazno = podrazumevano ponašanje pretraživača."""

    AUTO = "", _("Podrazumevano (bez direktive)")
    LARGE = "large", _("large — veliki pregled slike")
    STANDARD = "standard", _("standard — manji pregled")
    NONE = "none", _("none — bez pregleda slike")


class RobotsMaxSnippet(models.TextChoices):
    """Google max-snippet direktiva — prazno = podrazumevano ponašanje pretraživača."""

    AUTO = "", _("Podrazumevano (bez direktive)")
    UNLIMITED = "-1", _("-1 — bez ograničenja isečka")
    NONE = "0", _("0 — bez isečka u rezultatima")
