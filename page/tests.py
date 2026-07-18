"""Visual page builder conversion tests."""

from django.test import SimpleTestCase, TestCase, override_settings

from page.legacy_html import convert_ckeditor_html
from page.validation import validate_page


@override_settings(MEDIA_URL="/media/")
class LegacyHtmlConversionTests(SimpleTestCase):
    def test_converts_common_ckeditor_content_to_editable_blocks(self):
        html = """
            <h2>Naslov <strong>tretmana</strong></h2>
            <p>Opis sa <em>formatiranjem</em> i
               <a href="https://example.com">linkom</a>.</p>
            <figure class="image image-align-center">
              <img src="/media/uploads/2026/07/tretman.webp"
                   alt="Tretman lica" style="width: 80%">
              <figcaption>Rezultat tretmana</figcaption>
            </figure>
            <ul><li>Prva stavka</li><li>Druga stavka</li></ul>
        """

        page, plaintext = convert_ckeditor_html(html)
        blocks = page["sections"][0]["rows"][0]["columns"][0]["blocks"]

        self.assertEqual(validate_page(page), [])
        self.assertEqual(
            [block["type"] for block in blocks],
            ["heading", "text", "image", "text"],
        )
        self.assertIn("<strong>tretmana</strong>", blocks[0]["attrs"]["text"])
        self.assertIn("<em>formatiranjem</em>", blocks[1]["attrs"]["text"])
        self.assertEqual(blocks[2]["attrs"]["path"], "uploads/2026/07/tretman.webp")
        self.assertEqual(blocks[2]["attrs"]["alt"], "Tretman lica")
        self.assertEqual(blocks[2]["attrs"]["caption"], "Rezultat tretmana")
        self.assertIn("Naslov tretmana", plaintext)
        self.assertIn("Prva stavka", plaintext)

    def test_preserves_absolute_r2_image_url_and_extracts_storage_key(self):
        page, _ = convert_ckeditor_html(
            '<p><img src="https://media.example.com/media/uploads/photo.jpg"></p>'
        )
        block = page["sections"][0]["rows"][0]["columns"][0]["blocks"][0]

        self.assertEqual(block["attrs"]["src"], "https://media.example.com/media/uploads/photo.jpg")
        self.assertEqual(block["attrs"]["path"], "uploads/photo.jpg")
        self.assertEqual(block["attrs"]["alt"], "Slika")

    def test_empty_html_stays_empty(self):
        page, plaintext = convert_ckeditor_html("")

        self.assertEqual(page["sections"], [])
        self.assertEqual(plaintext, "")


class TreatmentBuilderModelTests(TestCase):
    def test_treatment_uses_builder_without_legacy_columns(self):
        from treatments.models import Treatment

        page, plaintext = convert_ckeditor_html(
            '<p>Sadržaj <strong>tretmana</strong>.</p>'
        )
        treatment = Treatment.objects.create(
            title_sr="Tretman",
            slug_sr="tretman",
            short_description_sr="Opis",
            body_page_sr=page,
            body_plaintext_sr=plaintext,
            page_version_sr=1,
            title_en="Treatment",
            slug_en="treatment",
            short_description_en="Description",
            price="100.00",
            is_active=True,
        )

        self.assertTrue(treatment.has_page_content("sr-latn"))
        self.assertFalse(hasattr(treatment, "legacy_full_description_sr"))
