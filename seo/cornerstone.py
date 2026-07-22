"""Cornerstone Content — klasteri, supporting članci i orphan upozorenja."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from blogs.models import BlogPost
from seo.content_analysis import build_content_analysis_input
from seo.content_text import normalize_whitespace
from seo.internal_linking_content import (
    ArticleLinkTarget,
    SiteLinkGraph,
    build_site_link_graph,
)
from seo.keyword_analyzer import CheckStatus, keyword_in_text

CORNERSTONE_LINK_BOOST = 18.0
CORNERSTONE_SORT_PRIORITY = 1000.0
SUPPORTING_RELATEDNESS_THRESHOLD = 8.0

STOPWORDS = {
    "i",
    "u",
    "na",
    "za",
    "se",
    "je",
    "su",
    "od",
    "do",
    "sa",
    "kao",
    "ili",
    "ali",
    "to",
    "ta",
    "te",
    "bi",
    "ne",
    "da",
    "a",
    "o",
    "iz",
    "po",
    "kod",
    "pri",
}


@dataclass(frozen=True)
class CornerstoneCheck:
    check_id: str
    label: str
    status: CheckStatus
    message: str


@dataclass(frozen=True)
class SupportingArticle:
    post_id: int
    title: str
    url: str
    links_to_cornerstone: bool
    relatedness_score: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ContentClusterRecommendation:
    cornerstone_post_id: int
    cornerstone_title: str
    cornerstone_url: str
    supporting_total: int
    supporting_linked: int
    missing_supporting_titles: tuple[str, ...]
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CornerstoneAnalysisResult:
    is_cornerstone: bool = False
    score: int = 0
    incoming_link_count: int = 0
    is_orphan: bool = False
    orphan_warning: str = ""
    parent_cornerstone: dict | None = None
    supporting_articles: list[SupportingArticle] = field(default_factory=list)
    cluster_recommendations: list[ContentClusterRecommendation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[CornerstoneCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "is_cornerstone": self.is_cornerstone,
            "score": self.score,
            "incoming_link_count": self.incoming_link_count,
            "is_orphan": self.is_orphan,
            "orphan_warning": self.orphan_warning,
            "parent_cornerstone": self.parent_cornerstone,
            "supporting_articles": [item.to_dict() for item in self.supporting_articles],
            "cluster_recommendations": [item.to_dict() for item in self.cluster_recommendations],
            "warnings": self.warnings,
            "checks": [
                {**asdict(check), "status": check.status.value}
                for check in self.checks
            ],
            "recommendations": self.recommendations,
            "message": self.message,
        }


def _content_tokens(text: str) -> set[str]:
    words = re.findall(r"[\w\u0100-\u024F]+", normalize_whitespace(text).lower())
    return {word for word in words if len(word) > 2 and word not in STOPWORDS}


def compute_article_relatedness(
    *,
    source_content: str,
    source_category_id: int | None,
    target: ArticleLinkTarget,
) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []
    source_tokens = _content_tokens(source_content)

    for phrase in target.link_phrases:
        if keyword_in_text(phrase, source_content):
            score += 4.0 + len(phrase.split())
            reasons.append(f'match "{phrase}"')
            break

    if source_category_id and source_category_id == target.category_id:
        score += 10.0
        reasons.append("same category")

    target_tokens = _content_tokens(" ".join(target.link_phrases))
    overlap = len(source_tokens & target_tokens)
    if overlap:
        score += min(overlap * 1.5, 12.0)
        reasons.append(f"{overlap} shared terms")

    if target.focus_keyword and keyword_in_text(target.focus_keyword, source_content):
        score += 8.0
        reasons.append(f'focus "{target.focus_keyword}"')

    reason = ", ".join(dict.fromkeys(reasons)) or "semantic closeness"
    return score, reason


def _cornerstone_targets(graph: SiteLinkGraph) -> list[ArticleLinkTarget]:
    return [
        target
        for target in graph.targets_by_id.values()
        if target.is_cornerstone
    ]


def _find_parent_cornerstone(
    *,
    post_id: int,
    content: str,
    category_id: int | None,
    graph: SiteLinkGraph,
) -> dict | None:
    cornerstones = _cornerstone_targets(graph)
    if not cornerstones:
        return None

    scored: list[tuple[float, str, ArticleLinkTarget]] = []
    for cornerstone in cornerstones:
        if cornerstone.post_id == post_id:
            continue
        score, reason = compute_article_relatedness(
            source_content=content,
            source_category_id=category_id,
            target=cornerstone,
        )
        if category_id and category_id == cornerstone.category_id:
            score += 5.0
        if score >= SUPPORTING_RELATEDNESS_THRESHOLD:
            scored.append((score, reason, cornerstone))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    score, reason, cornerstone = scored[0]
    links_to_parent = post_id in graph.outgoing and cornerstone.post_id in graph.outgoing[post_id]
    return {
        "post_id": cornerstone.post_id,
        "title": cornerstone.title,
        "url": cornerstone.url_path,
        "relatedness_score": round(score, 1),
        "reason": reason,
        "links_to_cornerstone": links_to_parent,
    }


def _find_supporting_articles(
    *,
    cornerstone: ArticleLinkTarget,
    graph: SiteLinkGraph,
) -> list[SupportingArticle]:
    supporting: list[SupportingArticle] = []

    for target in graph.targets_by_id.values():
        if target.post_id == cornerstone.post_id or target.is_cornerstone:
            continue

        score, reason = compute_article_relatedness(
            source_content=" ".join(cornerstone.link_phrases),
            source_category_id=cornerstone.category_id,
            target=target,
        )
        if cornerstone.category_id and cornerstone.category_id == target.category_id:
            score += 4.0

        if score < SUPPORTING_RELATEDNESS_THRESHOLD:
            continue

        links_to_cornerstone = cornerstone.post_id in graph.outgoing.get(target.post_id, set())
        supporting.append(
            SupportingArticle(
                post_id=target.post_id,
                title=target.title,
                url=target.url_path,
                links_to_cornerstone=links_to_cornerstone,
                relatedness_score=round(score, 1),
                reason=reason,
            )
        )

    supporting.sort(key=lambda item: item.relatedness_score, reverse=True)
    return supporting[:12]


def build_content_cluster_recommendations(
    graph: SiteLinkGraph,
    *,
    focus_post_id: int | None = None,
) -> list[ContentClusterRecommendation]:
    recommendations: list[ContentClusterRecommendation] = []

    for cornerstone in _cornerstone_targets(graph):
        supporting = _find_supporting_articles(cornerstone=cornerstone, graph=graph)
        if focus_post_id:
            supporting_ids = {item.post_id for item in supporting}
            is_relevant = focus_post_id == cornerstone.post_id or focus_post_id in supporting_ids
            if not is_relevant:
                continue

        linked = [item for item in supporting if item.links_to_cornerstone]
        missing = [item.title for item in supporting if not item.links_to_cornerstone]

        if not supporting:
            recommendation = (
                f"Cornerstone \"{cornerstone.title}\" has no identified supporting posts — "
                "publish related topics or add keywords."
            )
        elif missing:
            recommendation = (
                f"{len(missing)} supporting post(s) still do not link to cornerstone "
                f'"{cornerstone.title}".'
            )
        else:
            recommendation = (
                f"Cluster around \"{cornerstone.title}\" is well connected "
                f"({len(linked)} supporting posts)."
            )

        recommendations.append(
            ContentClusterRecommendation(
                cornerstone_post_id=cornerstone.post_id,
                cornerstone_title=cornerstone.title,
                cornerstone_url=cornerstone.url_path,
                supporting_total=len(supporting),
                supporting_linked=len(linked),
                missing_supporting_titles=tuple(missing[:8]),
                recommendation=recommendation,
            )
        )

    return recommendations


def _build_orphan_warning(
    *,
    post_id: int,
    incoming_count: int,
    is_cornerstone: bool,
) -> tuple[bool, str]:
    if incoming_count > 0:
        return False, ""

    if is_cornerstone:
        return True, (
            "Cornerstone post has no incoming links — supporting posts should "
            "point to this content."
        )

    return True, (
        "Orphan content — no other post links to this one. "
        "Add a link from related posts or the cornerstone cluster."
    )


def _score_cornerstone_health(
    *,
    is_cornerstone: bool,
    is_orphan: bool,
    incoming_count: int,
    parent_cornerstone: dict | None,
    supporting_articles: list[SupportingArticle],
) -> tuple[int, list[CornerstoneCheck]]:
    checks: list[CornerstoneCheck] = []
    points = 0
    max_points = 0

    if is_orphan:
        orphan_status = CheckStatus.BAD
        orphan_message = "Post is an orphan — no incoming internal links."
        orphan_points = 0
    else:
        orphan_status = CheckStatus.GOOD
        orphan_message = f"Post has {incoming_count} incoming internal link(s)."
        orphan_points = 25

    checks.append(
        CornerstoneCheck(
            check_id="orphan_status",
            label="Orphan content",
            status=orphan_status,
            message=orphan_message,
        )
    )
    points += orphan_points
    max_points += 25

    if is_cornerstone:
        if not supporting_articles:
            support_status = CheckStatus.OK
            support_message = "No supporting posts — publish related topics."
            support_points = 10
        else:
            linked = sum(1 for item in supporting_articles if item.links_to_cornerstone)
            ratio = linked / len(supporting_articles)
            if ratio >= 0.7:
                support_status = CheckStatus.GOOD
                support_message = f"{linked}/{len(supporting_articles)} supporting posts link to the cornerstone."
                support_points = 35
            elif ratio >= 0.4:
                support_status = CheckStatus.OK
                support_message = f"{linked}/{len(supporting_articles)} supporting posts link — increase coverage."
                support_points = 22
            else:
                support_status = CheckStatus.BAD
                support_message = f"Only {linked}/{len(supporting_articles)} supporting posts link to the cornerstone."
                support_points = 8

        checks.append(
            CornerstoneCheck(
                check_id="supporting_coverage",
                label="Supporting posts",
                status=support_status,
                message=support_message,
            )
        )
        points += support_points
        max_points += 35

        incoming_status = CheckStatus.GOOD if incoming_count >= 2 else CheckStatus.OK if incoming_count else CheckStatus.BAD
        incoming_message = (
            f"Cornerstone has {incoming_count} incoming link(s)."
            if incoming_count
            else "Cornerstone has no incoming links from supporting posts."
        )
        incoming_points = 20 if incoming_count >= 2 else 12 if incoming_count else 0
        checks.append(
            CornerstoneCheck(
                check_id="cornerstone_incoming",
                label="Incoming links",
                status=incoming_status,
                message=incoming_message,
            )
        )
        points += incoming_points
        max_points += 20
    else:
        if parent_cornerstone:
            if parent_cornerstone.get("links_to_cornerstone"):
                parent_status = CheckStatus.GOOD
                parent_message = f'Linked to cornerstone "{parent_cornerstone["title"]}".'
                parent_points = 40
            else:
                parent_status = CheckStatus.BAD
                parent_message = (
                    f"Add a link to cornerstone \"{parent_cornerstone['title']}\" "
                    "in this post."
                )
                parent_points = 5
        else:
            parent_status = CheckStatus.NEUTRAL
            parent_message = "No cornerstone cluster assigned — mark the main topic post."
            parent_points = 20

        checks.append(
            CornerstoneCheck(
                check_id="parent_cornerstone",
                label="Cornerstone cluster",
                status=parent_status,
                message=parent_message,
            )
        )
        points += parent_points
        max_points += 40

    score = round((points / max_points) * 100) if max_points else 0
    return score, checks


def analyze_cornerstone_content(
    content_object,
    metadata=None,
    *,
    overrides: dict | None = None,
    visible_only: bool = False,
) -> CornerstoneAnalysisResult:
    if not isinstance(content_object, BlogPost):
        return CornerstoneAnalysisResult(
            message="Cornerstone analysis is available for blog posts only.",
        )

    if content_object.pk is None:
        return CornerstoneAnalysisResult(
            message="Save the post to see the cornerstone analysis.",
        )

    is_cornerstone = bool(metadata and metadata.is_cornerstone)
    if overrides and "is_cornerstone" in overrides:
        is_cornerstone = bool(overrides["is_cornerstone"])

    analysis_input = build_content_analysis_input(
        content_object,
        metadata,
        overrides=overrides,
        visible_only=visible_only,
    )
    content = analysis_input.content

    graph = build_site_link_graph(include_pk=content_object.pk)
    post_id = content_object.pk
    incoming_count = len(graph.incoming.get(post_id, set()))
    is_orphan, orphan_warning = _build_orphan_warning(
        post_id=post_id,
        incoming_count=incoming_count,
        is_cornerstone=is_cornerstone,
    )

    warnings: list[str] = []
    if is_orphan and orphan_warning:
        warnings.append(orphan_warning)

    parent_cornerstone = None
    supporting_articles: list[SupportingArticle] = []

    if is_cornerstone:
        cornerstone_target = graph.targets_by_id.get(post_id)
        if cornerstone_target is not None:
            if is_cornerstone != cornerstone_target.is_cornerstone:
                cornerstone_target = ArticleLinkTarget(
                    post_id=cornerstone_target.post_id,
                    title=cornerstone_target.title,
                    slug=cornerstone_target.slug,
                    url_path=cornerstone_target.url_path,
                    focus_keyword=cornerstone_target.focus_keyword,
                    secondary_keywords=cornerstone_target.secondary_keywords,
                    category_id=cornerstone_target.category_id,
                    is_cornerstone=True,
                    link_phrases=cornerstone_target.link_phrases,
                )
            supporting_articles = _find_supporting_articles(
                cornerstone=cornerstone_target,
                graph=graph,
            )
            missing = [item.title for item in supporting_articles if not item.links_to_cornerstone]
            if missing:
                warnings.append(
                    f"{len(missing)} supporting post(s) do not link to this cornerstone post."
                )
    else:
        parent_cornerstone = _find_parent_cornerstone(
            post_id=post_id,
            content=content,
            category_id=getattr(content_object, "category_id", None),
            graph=graph,
        )
        if parent_cornerstone and not parent_cornerstone.get("links_to_cornerstone"):
            warnings.append(
                f'Add a link to cornerstone "{parent_cornerstone["title"]}".'
            )

    cluster_recommendations = build_content_cluster_recommendations(
        graph,
        focus_post_id=post_id,
    )
    if not cluster_recommendations and _cornerstone_targets(graph):
        cluster_recommendations = build_content_cluster_recommendations(graph)[:3]

    score, checks = _score_cornerstone_health(
        is_cornerstone=is_cornerstone,
        is_orphan=is_orphan,
        incoming_count=incoming_count,
        parent_cornerstone=parent_cornerstone,
        supporting_articles=supporting_articles,
    )

    recommendations: list[str] = list(warnings)
    for cluster in cluster_recommendations:
        if cluster.missing_supporting_titles:
            recommendations.append(cluster.recommendation)

    if is_cornerstone and supporting_articles:
        for item in supporting_articles:
            if not item.links_to_cornerstone:
                recommendations.append(
                    f'Have "{item.title}" link to this cornerstone post.'
                )

    if not recommendations:
        recommendations.append("Cornerstone cluster is well structured.")

    return CornerstoneAnalysisResult(
        is_cornerstone=is_cornerstone,
        score=score,
        incoming_link_count=incoming_count,
        is_orphan=is_orphan,
        orphan_warning=orphan_warning,
        parent_cornerstone=parent_cornerstone,
        supporting_articles=supporting_articles,
        cluster_recommendations=cluster_recommendations,
        warnings=warnings,
        checks=checks,
        recommendations=recommendations[:12],
    )
